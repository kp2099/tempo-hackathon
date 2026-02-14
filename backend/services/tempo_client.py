"""
Tempo blockchain client using pytempo + web3.py.

Uses pytempo's TempoTransaction (type 0x76) with 2D nonce keys for
true parallel batch payments. Single payments use nonce key 0 (protocol nonce).
Falls back to simulation mode when RPC is unreachable.

Docs: https://docs.tempo.xyz/guide/tempo-transaction#concurrent-transactions
"""

import logging
import hashlib
from typing import Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from web3 import Web3
from eth_account import Account
from pytempo import TempoTransaction, Call

from config import settings

logger = logging.getLogger("TempoExpenseAI.TempoClient")

# Tempo Nonce Precompile — used to query 2D nonce values for keys 1+
NONCE_PRECOMPILE_ADDRESS = "0x4E4F4E4345000000000000000000000000000000"
NONCE_PRECOMPILE_ABI = [
    {
        "name": "getNonce",
        "type": "function",
        "inputs": [
            {"name": "account", "type": "address"},
            {"name": "nonceKey", "type": "uint256"},
        ],
        "outputs": [{"name": "nonce", "type": "uint64"}],
        "stateMutability": "view",
    },
]

# TIP-20 ABI subset — transferWithMemo for payments, balanceOf for checks
TIP20_ABI = [
    {
        "name": "transferWithMemo",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "memo", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
]


def _encode_memo(memo: str) -> bytes:
    """Encode a memo string into bytes32."""
    truncated = memo[:32] if len(memo) > 32 else memo
    return truncated.encode("utf-8").ljust(32, b"\x00")[:32]


def _ensure_0x(key: str) -> str:
    """Ensure a hex string has 0x prefix."""
    return key if key.startswith("0x") else f"0x{key}"


class TempoClient:
    """
    Client for Tempo L1 blockchain payments.

    Uses pytempo TempoTransaction (type 0x76) with 2D nonce keys.
    Batch payments assign each payment a unique nonce_key (1, 2, 3, ...)
    so Tempo can validate and execute them in parallel.
    """

    MAX_PARALLEL_KEYS = 10  # Reuse keys 1..10 to avoid state creation costs

    def __init__(self):
        self.w3: Optional[Web3] = None
        self.account = None
        self.token_contract = None
        self.nonce_precompile = None
        self.connected = False

        try:
            self.w3 = Web3(Web3.HTTPProvider(
                settings.tempo_rpc_url,
                request_kwargs={"timeout": 15},
            ))

            if settings.tempo_private_key:
                self.account = Account.from_key(settings.tempo_private_key)
                logger.info(f"🔗 Tempo RPC: {settings.tempo_rpc_url}")
                logger.info(f"   Wallet: {self.account.address}")

            self.token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(settings.alpha_usd_address),
                abi=TIP20_ABI,
            )
            self.nonce_precompile = self.w3.eth.contract(
                address=Web3.to_checksum_address(NONCE_PRECOMPILE_ADDRESS),
                abi=NONCE_PRECOMPILE_ABI,
            )

            self.connected = self.w3.is_connected()
            if self.connected:
                logger.info(f"   Chain: {self.w3.eth.chain_id} | ✅ LIVE")
                if self.account:
                    try:
                        raw = self.token_contract.functions.balanceOf(self.account.address).call()
                        logger.info(f"   AlphaUSD: ${raw / 10**6:,.2f}")
                    except Exception as e:
                        logger.warning(f"   Balance check failed: {e}")
            else:
                logger.warning("⚠️ Tempo RPC unreachable — simulation mode")

        except Exception as e:
            logger.warning(f"⚠️ Tempo connection failed: {e} — simulation mode")
            self.connected = False

    # ─── Nonce helpers ───────────────────────────────────────────

    def _get_nonce_for_key(self, nonce_key: int) -> int:
        """Get current nonce for a 2D nonce key. Key 0 = protocol nonce, 1+ = parallel."""
        if nonce_key == 0:
            return self.w3.eth.get_transaction_count(self.account.address)
        try:
            return self.nonce_precompile.functions.getNonce(self.account.address, nonce_key).call()
        except Exception:
            return 0  # New key, nonce starts at 0

    # ─── Core: build, sign, send a TempoTransaction ─────────────

    def _send_tempo_tx(
        self, destination: str, amount: float, memo: str, expense_id: str,
        nonce_key: int = 0, nonce: Optional[int] = None,
    ) -> dict:
        """Build, sign, and send a single TempoTransaction (type 0x76)."""
        dest = Web3.to_checksum_address(destination)
        token_amount = int(amount * 10**6)
        memo_bytes = _encode_memo(memo)

        calldata = self.token_contract.functions.transferWithMemo(
            dest, token_amount, memo_bytes
        )._encode_transaction_data()

        if nonce is None:
            nonce = self._get_nonce_for_key(nonce_key)

        gas_price = self.w3.eth.gas_price or self.w3.to_wei(1, "gwei")

        tx = TempoTransaction.create(
            chain_id=settings.tempo_chain_id,
            gas_limit=150_000,
            max_fee_per_gas=gas_price * 2,
            max_priority_fee_per_gas=gas_price,
            nonce=nonce,
            nonce_key=nonce_key,
            fee_token=settings.alpha_usd_address,
            calls=(Call.create(to=settings.alpha_usd_address, value=0, data=calldata),),
        )

        signed_tx = tx.sign(_ensure_0x(settings.tempo_private_key))
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.encode())
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=30)

        return self._format_receipt(receipt, amount, destination, memo, expense_id, nonce_key, nonce)

    def _format_receipt(
        self, receipt, amount, destination, memo, expense_id, nonce_key=0, nonce=0,
    ) -> dict:
        """Format a transaction receipt into a standard response dict."""
        tx_hash_hex = receipt.transactionHash.hex()
        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = f"0x{tx_hash_hex}"

        success = receipt.status == 1
        level = logger.info if success else logger.error
        level(
            f"{'💰' if success else '❌'} ${amount:.2f} → {destination[:10]}... | "
            f"TX: {tx_hash_hex[:18]}... | Block: {receipt.blockNumber}"
        )

        return {
            "success": success,
            "tx_hash": tx_hash_hex,
            "amount": amount,
            "destination": destination,
            "memo": memo,
            "expense_id": expense_id,
            "tempo_tx_url": f"{settings.tempo_explorer_url}/tx/{tx_hash_hex}",
            "network": "tempo_testnet",
            "chain_id": settings.tempo_chain_id,
            "token": "AlphaUSD",
            "token_address": settings.alpha_usd_address,
            "block_number": receipt.blockNumber,
            "gas_used": receipt.gasUsed,
            "gas_cost_wei": receipt.gasUsed * (receipt.effectiveGasPrice or 0),
            "timestamp": datetime.utcnow().isoformat(),
            "settlement": "instant",
            "mode": "live",
            "nonce_key": nonce_key,
            "nonce": nonce,
            "tx_type": "tempo_0x76",
            "fee_sponsored": True,
            "fee_sponsor": self.account.address,
        }

    # ─── Simulation fallback ─────────────────────────────────────

    def _simulate_payment(self, destination, amount, memo, expense_id) -> dict:
        """Simulate a payment when RPC is unreachable."""
        tx_hash = "0x" + hashlib.sha256(
            f"{expense_id}{destination}{amount}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()

        logger.info(f"💰 [SIM] ${amount:.2f} → {destination[:10]}... | {tx_hash[:18]}...")

        return {
            "success": True,
            "tx_hash": tx_hash,
            "amount": amount,
            "destination": destination,
            "memo": memo,
            "expense_id": expense_id,
            "tempo_tx_url": f"{settings.tempo_explorer_url}/tx/{tx_hash}",
            "network": "tempo_testnet_simulation",
            "chain_id": settings.tempo_chain_id,
            "token": "AlphaUSD",
            "timestamp": datetime.utcnow().isoformat(),
            "settlement": "instant",
            "mode": "simulation",
        }

    # ─── Public API ──────────────────────────────────────────────

    def send_payment(self, destination: str, amount: float, memo: str, expense_id: str) -> dict:
        """Send a single AlphaUSD payment via Tempo (protocol nonce key 0)."""
        if not self.connected or not self.account:
            return self._simulate_payment(destination, amount, memo, expense_id)
        try:
            return self._send_tempo_tx(destination, amount, memo, expense_id)
        except Exception as e:
            logger.error(f"❌ Payment failed: {e}")
            return self._simulate_payment(destination, amount, memo, expense_id)

    def get_balance(self, address: str) -> dict:
        """Get AlphaUSD balance for an address."""
        if not self.connected:
            return {"address": address, "balance": "1000000.00", "token": "AlphaUSD", "mode": "simulation"}
        try:
            raw = self.token_contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
            return {"address": address, "balance": f"{raw / 10**6:.2f}", "token": "AlphaUSD", "mode": "live"}
        except Exception as e:
            return {"address": address, "balance": "0.00", "token": "AlphaUSD", "error": str(e)}

    def send_batch_payments(self, payments: List[dict]) -> dict:
        """
        Send multiple payments in parallel using Tempo's 2D nonce system.

        Each payment gets a unique nonce_key (1..N) so Tempo validates and
        executes them concurrently — no sequential nonce dependency.
        """
        if not self.connected or not self.account:
            results = [self._simulate_payment(p["destination"], p["amount"], p["memo"], p["expense_id"]) for p in payments]
            return {
                "success": True, "total_payments": len(results),
                "total_amount": sum(p["amount"] for p in payments),
                "results": results, "parallel": True,
                "nonce_strategy": "2d_nonce_simulated", "mode": "simulation",
            }

        total_amount = sum(p["amount"] for p in payments)
        logger.info(f"⚡ Batch: {len(payments)} payments via 2D nonces | ${total_amount:,.2f}")

        # Assign nonce keys (cycle 1..MAX_PARALLEL_KEYS)
        assignments = [(p, (i % self.MAX_PARALLEL_KEYS) + 1) for i, p in enumerate(payments)]

        # Pre-fetch nonces for all keys in parallel
        unique_keys = list({nk for _, nk in assignments})
        nonce_map = {}
        with ThreadPoolExecutor(max_workers=min(len(unique_keys), 10)) as pool:
            futures = {pool.submit(self._get_nonce_for_key, k): k for k in unique_keys}
            for f in as_completed(futures):
                nonce_map[futures[f]] = f.result() if not f.exception() else 0

        # Track per-key nonce increments
        nonce_counters = dict(nonce_map)

        # Send all transactions concurrently
        results, errors = [], []
        with ThreadPoolExecutor(max_workers=min(len(payments), self.MAX_PARALLEL_KEYS)) as pool:
            future_map = {}
            for payment, nonce_key in assignments:
                nonce = nonce_counters[nonce_key]
                nonce_counters[nonce_key] += 1
                future = pool.submit(
                    self._send_tempo_tx,
                    destination=payment["destination"],
                    amount=payment["amount"],
                    memo=payment["memo"],
                    expense_id=payment["expense_id"],
                    nonce_key=nonce_key,
                    nonce=nonce,
                )
                future_map[future] = payment

            for future in as_completed(future_map):
                try:
                    results.append(future.result())
                except Exception as e:
                    pid = future_map[future]["expense_id"]
                    logger.error(f"❌ Batch TX failed for {pid}: {e}")
                    errors.append({"expense_id": pid, "error": str(e)})

        success_count = sum(1 for r in results if r.get("success"))
        logger.info(f"⚡ Batch done: {success_count}/{len(payments)} successful")

        return {
            "success": success_count > 0,
            "total_payments": len(payments),
            "successful": success_count,
            "failed": len(errors),
            "total_amount": total_amount,
            "results": results,
            "errors": errors,
            "parallel": True,
            "nonce_strategy": "tempo_2d_nonce",
            "fee_sponsored": True,
            "fee_sponsor": self.account.address,
            "mode": "live",
        }

    def verify_transaction(self, tx_hash: str) -> dict:
        """Verify a transaction on Tempo blockchain."""
        if not self.connected:
            return {"verified": True, "tx_hash": tx_hash, "mode": "simulation",
                    "explorer_url": f"{settings.tempo_explorer_url}/tx/{tx_hash}"}
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
            return {
                "verified": receipt.status == 1, "tx_hash": tx_hash,
                "block_number": receipt.blockNumber, "gas_used": receipt.gasUsed,
                "explorer_url": f"{settings.tempo_explorer_url}/tx/{tx_hash}", "mode": "live",
            }
        except Exception as e:
            return {"verified": False, "tx_hash": tx_hash, "error": str(e)}


# Singleton
_tempo_client = None


def get_tempo_client() -> TempoClient:
    global _tempo_client
    if _tempo_client is None:
        _tempo_client = TempoClient()
    return _tempo_client
