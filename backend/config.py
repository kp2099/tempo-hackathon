"""Application configuration loaded from environment variables."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Tempo Blockchain (EVM Layer 1 — Moderato Testnet)
    tempo_rpc_url: str = "https://rpc.moderato.tempo.xyz"
    tempo_chain_id: int = 42431
    tempo_private_key: str = ""  # Master agent wallet private key
    tempo_explorer_url: str = "https://explore.tempo.xyz"

    # TIP-20 Stablecoin (AlphaUSD on testnet)
    alpha_usd_address: str = "0x20c0000000000000000000000000000000000001"

    # AI Agent Thresholds
    risk_threshold_auto_approve: float = 0.3
    risk_threshold_auto_reject: float = 0.7
    max_auto_approve_amount: float = 2000.0

    # App
    database_url: str = "sqlite:///./tempoexpense.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
