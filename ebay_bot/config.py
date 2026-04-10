"""Configuration helpers for EbayBot.

Values are read from environment variables (or a .env file) so that no
secrets are ever stored in source code.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Return the value of an environment variable, raising if it is missing."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "Copy .env.example to .env and fill in your eBay API credentials."
        )
    return value


class Config:
    """All configuration values needed by EbayBot."""

    def __init__(self) -> None:
        self.app_id: str = _require("EBAY_APP_ID")
        self.dev_id: str = _require("EBAY_DEV_ID")
        self.cert_id: str = _require("EBAY_CERT_ID")
        self.user_token: str = _require("EBAY_USER_TOKEN")
        self.sandbox: bool = os.environ.get("EBAY_SANDBOX", "True").lower() in (
            "1",
            "true",
            "yes",
        )
        self.poll_interval: int = int(os.environ.get("BOT_POLL_INTERVAL", "300"))
        self.low_stock_threshold: int = int(
            os.environ.get("LOW_STOCK_THRESHOLD", "5")
        )
