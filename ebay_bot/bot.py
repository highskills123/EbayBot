"""Core EbayBot logic.

The bot polls the eBay API on a configurable interval and performs the
following automated tasks:

* Logs a summary of the seller's account metrics.
* Checks for new/active orders and logs each one.
* Flags listings whose quantity has fallen below the configured threshold.
* Automatically relists any item that has ended (quantity == 0 and status ended).
"""

from __future__ import annotations

import time
from typing import Any

import schedule

from ebay_bot.api import EbayAPI, EbayAPIError
from ebay_bot.config import Config
from ebay_bot.utils import get_logger, format_price

logger = get_logger(__name__)


class EbayBot:
    """Manages an eBay shop automatically."""

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._api = EbayAPI(self._config)

    # ------------------------------------------------------------------
    # Public helpers (also called by the scheduler below)
    # ------------------------------------------------------------------

    def print_summary(self) -> dict[str, Any]:
        """Fetch and log the seller summary; return the raw dict."""
        logger.info("=== Seller Summary ===")
        try:
            summary = self._api.get_seller_summary()
        except EbayAPIError as exc:
            logger.error("Could not fetch seller summary: %s", exc)
            return {}

        active_count = summary.get("ActiveListingCount", "N/A")
        sold_count = summary.get("QuantitySold", "N/A")
        logger.info("Active listings : %s", active_count)
        logger.info("Items sold      : %s", sold_count)
        return summary

    def check_orders(self, days_back: int = 7) -> list[dict[str, Any]]:
        """Fetch recent orders and log a line per order; return the list."""
        logger.info("=== Recent Orders (last %d days) ===", days_back)
        try:
            orders = self._api.get_orders(order_status="Active", days_back=days_back)
        except EbayAPIError as exc:
            logger.error("Could not fetch orders: %s", exc)
            return []

        if not orders:
            logger.info("No active orders found.")
            return []

        for order in orders:
            order_id = order.get("OrderID", "?")
            total = order.get("Total", {})
            amount = getattr(total, "_", None) or total.get("_", "?")
            currency = getattr(total, "currencyID", None) or total.get(
                "@currencyID", "USD"
            )
            status = order.get("OrderStatus", "?")
            logger.info(
                "Order %s | status: %s | total: %s",
                order_id,
                status,
                format_price(float(amount), currency) if amount != "?" else "N/A",
            )

        return orders

    def check_inventory(self) -> list[dict[str, Any]]:
        """Check all active listings for low stock; return low-stock items."""
        logger.info("=== Inventory Check ===")
        threshold = self._config.low_stock_threshold
        try:
            listings = self._api.get_active_listings()
        except EbayAPIError as exc:
            logger.error("Could not fetch listings: %s", exc)
            return []

        low_stock: list[dict[str, Any]] = []
        for item in listings:
            item_id = item.get("ItemID", "?")
            title = item.get("Title", "Untitled")
            quantity = int(item.get("QuantityAvailable", 0))
            if quantity < threshold:
                logger.warning(
                    "LOW STOCK: item %s ('%s') has only %d unit(s) left.",
                    item_id,
                    title,
                    quantity,
                )
                low_stock.append(item)

        if not low_stock:
            logger.info("All listings have sufficient stock (threshold=%d).", threshold)

        return low_stock

    def relist_ended_items(self) -> list[str]:
        """Relist any ended items; return new item IDs."""
        logger.info("=== Relist Ended Items ===")
        try:
            # GetMyeBaySelling with UnsoldList gives us ended items
            from ebaysdk.exception import ConnectionError as EbayConnectionError

            response = self._api._trading.execute(
                "GetMyeBaySelling",
                {
                    "UnsoldList": {
                        "Include": True,
                        "Pagination": {"EntriesPerPage": 100, "PageNumber": 1},
                    }
                },
            )
        except Exception as exc:
            logger.error("Could not fetch unsold listings: %s", exc)
            return []

        reply = response.reply
        unsold = getattr(reply, "UnsoldList", None)
        if not unsold:
            logger.info("No ended/unsold items found.")
            return []

        items_obj = getattr(unsold, "ItemArray", None)
        if not items_obj:
            logger.info("No ended/unsold items found.")
            return []

        item_list = items_obj.Item
        if not isinstance(item_list, list):
            item_list = [item_list]

        new_ids: list[str] = []
        for item in item_list:
            item_id = getattr(item, "ItemID", None)
            if not item_id:
                continue
            try:
                new_id = self._api.relist_item(item_id)
                new_ids.append(new_id)
            except EbayAPIError as exc:
                logger.error("Failed to relist item %s: %s", item_id, exc)

        logger.info("Relisted %d item(s).", len(new_ids))
        return new_ids

    # ------------------------------------------------------------------
    # Scheduler / main run loop
    # ------------------------------------------------------------------

    def _run_cycle(self) -> None:
        """Run one full bot cycle."""
        self.print_summary()
        self.check_orders()
        self.check_inventory()
        self.relist_ended_items()

    def run(self) -> None:
        """Start the bot; runs indefinitely, polling every ``poll_interval`` seconds."""
        interval = self._config.poll_interval
        logger.info(
            "EbayBot starting. Poll interval: %d seconds. Sandbox: %s.",
            interval,
            self._config.sandbox,
        )

        # Run once immediately, then on the schedule.
        self._run_cycle()

        schedule.every(interval).seconds.do(self._run_cycle)

        while True:
            schedule.run_pending()
            time.sleep(1)
