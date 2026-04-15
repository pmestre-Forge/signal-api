"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # x402 payment config
    evm_address: str = ""
    network: str = "eip155:84532"  # Base Sepolia testnet
    facilitator_url: str = "https://x402.org/facilitator"

    # Pricing in USD
    price_signal: str = "0.005"
    price_scan: str = "0.01"
    price_risk: str = "0.01"

    # Data config
    cache_ttl_seconds: int = 300  # 5 min cache for market data

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
