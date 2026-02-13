"""Application configuration loaded from environment variables."""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Stellar / Tempo Network
    stellar_network: str = "testnet"
    stellar_horizon_url: str = "https://horizon-testnet.stellar.org"
    stellar_secret_key: str = ""
    stellar_public_key: str = ""

    # Stablecoin Asset
    stablecoin_code: str = "USDC"
    stablecoin_issuer: str = ""

    # AI Agent Thresholds
    risk_threshold_auto_approve: float = 0.3
    risk_threshold_auto_reject: float = 0.7
    max_auto_approve_amount: float = 500.0

    # App
    database_url: str = "sqlite:///./tempoexpense.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

