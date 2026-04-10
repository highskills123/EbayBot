"""Entry point for EbayBot.

Usage
-----
1. Copy .env.example to .env and fill in your eBay API credentials.
2. Install dependencies:

       pip install -r requirements.txt

3. Run the bot:

       python main.py

The bot will immediately run one full cycle and then repeat every
``BOT_POLL_INTERVAL`` seconds (default 5 minutes).
"""

from ebay_bot.bot import EbayBot


def main() -> None:
    bot = EbayBot()
    bot.run()


if __name__ == "__main__":
    main()
