# EbayBot

An automated bot to help manage your eBay shop. It connects to the eBay
Trading API and periodically:

- 📊 Logs a **seller summary** (active listings, items sold, etc.)
- 📦 Checks **active orders** and logs their status
- ⚠️  Flags **low-stock listings** when quantity drops below a configurable threshold
- 🔄 **Relists ended items** automatically so nothing falls off eBay

---

## Requirements

- Python 3.9+
- An [eBay Developer](https://developer.ebay.com/) account with API keys
- An eBay User Token with Trading API access

---

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/highskills123/EbayBot.git
cd EbayBot
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure credentials

Copy the example environment file and fill in your eBay API credentials:

```bash
cp .env.example .env
```

Then edit `.env`:

```ini
EBAY_APP_ID=your_app_id_here
EBAY_DEV_ID=your_dev_id_here
EBAY_CERT_ID=your_cert_id_here
EBAY_USER_TOKEN=your_user_token_here

# True = sandbox (for testing), False = live production
EBAY_SANDBOX=True

# How often (in seconds) the bot should poll eBay (default: 300 = 5 min)
BOT_POLL_INTERVAL=300

# Warn when a listing has fewer than this many units remaining (default: 5)
LOW_STOCK_THRESHOLD=5
```

> ⚠️ **Never commit your `.env` file.** It is already in `.gitignore`.

### 3. Run the bot

```bash
python main.py
```

The bot runs one full cycle immediately, then repeats on the configured
interval until you stop it with `Ctrl+C`.

---

## Project structure

```
EbayBot/
├── ebay_bot/
│   ├── __init__.py     # Package entry, exports EbayBot
│   ├── api.py          # Thin wrapper around the eBay Trading API
│   ├── bot.py          # Core bot logic and scheduler
│   ├── config.py       # Configuration loaded from environment variables
│   └── utils.py        # Logging, date/time, and formatting helpers
├── tests/
│   ├── test_api.py     # Unit tests for EbayAPI
│   ├── test_bot.py     # Unit tests for EbayBot
│   ├── test_config.py  # Unit tests for Config
│   └── test_utils.py   # Unit tests for utilities
├── main.py             # Entry point
├── requirements.txt    # Runtime dependencies
├── requirements-dev.txt# Dev / test dependencies
└── .env.example        # Environment variable template
```

---

## Running tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

## Using the bot programmatically

You can also import and call individual methods from your own scripts:

```python
from ebay_bot.bot import EbayBot

bot = EbayBot()

# Get seller summary
summary = bot.print_summary()

# Check recent orders
orders = bot.check_orders(days_back=7)

# Find low-stock listings
low_stock = bot.check_inventory()

# Relist any ended items
new_ids = bot.relist_ended_items()
```

To update a listing's price or quantity directly via the API wrapper:

```python
from ebay_bot.api import EbayAPI
from ebay_bot.config import Config

api = EbayAPI(Config())
api.update_price("ITEM_ID", 14.99)
api.update_quantity("ITEM_ID", 20)
```

---

## Getting eBay API credentials

1. Sign up at <https://developer.ebay.com/>
2. Create an application to get your **App ID**, **Dev ID**, and **Cert ID**
3. Generate a **User Token** via the eBay OAuth flow (use the sandbox token
   for testing, production token for your live shop)

---

## License

MIT
