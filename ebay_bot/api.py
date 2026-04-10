"""Thin wrapper around the eBay Trading API and Finding API.

Uses the ``ebaysdk`` library under the hood so the rest of the code can
work with plain Python dicts instead of raw XML responses.
"""

from __future__ import annotations

from typing import Any

from ebaysdk.exception import ConnectionError as EbayConnectionError
from ebaysdk.trading import Connection as Trading
from ebaysdk.finding import Connection as Finding

from ebay_bot.config import Config
from ebay_bot.utils import get_logger

logger = get_logger(__name__)


class EbayAPIError(Exception):
    """Raised when an eBay API call fails."""


class EbayAPI:
    """Wrapper around the eBay SDK connections."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._trading = Trading(
            appid=config.app_id,
            devid=config.dev_id,
            certid=config.cert_id,
            token=config.user_token,
            config_file=None,
            siteid="0",  # US site
            sandbox=config.sandbox,
        )
        self._finding = Finding(
            appid=config.app_id,
            config_file=None,
            siteid="EBAY-US",
            sandbox=config.sandbox,
        )

    # ------------------------------------------------------------------
    # Seller listings
    # ------------------------------------------------------------------

    def get_active_listings(self, entries_per_page: int = 100) -> list[dict[str, Any]]:
        """Return a list of all active seller listings.

        Each entry is a plain dict taken directly from the eBay response.
        """
        listings: list[dict[str, Any]] = []
        page = 1

        while True:
            try:
                response = self._trading.execute(
                    "GetMyeBaySelling",
                    {
                        "ActiveList": {
                            "Include": True,
                            "Pagination": {
                                "EntriesPerPage": entries_per_page,
                                "PageNumber": page,
                            },
                        }
                    },
                )
            except EbayConnectionError as exc:
                raise EbayAPIError(f"GetMyeBaySelling failed: {exc}") from exc

            reply = response.reply
            active = getattr(reply, "ActiveList", None)
            if not active:
                break

            items = getattr(active, "ItemArray", None)
            if not items:
                break

            item_list = items.Item
            if not isinstance(item_list, list):
                item_list = [item_list]

            for item in item_list:
                listings.append(item.__dict__)

            pagination = getattr(active, "PaginationResult", None)
            if pagination is None:
                break

            total_pages = int(getattr(pagination, "TotalNumberOfPages", 1))
            if page >= total_pages:
                break
            page += 1

        logger.info("Fetched %d active listing(s).", len(listings))
        return listings

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def get_orders(
        self, order_status: str = "Active", days_back: int = 30
    ) -> list[dict[str, Any]]:
        """Return recent orders from the seller's account.

        Parameters
        ----------
        order_status:
            eBay order status filter – ``"Active"``, ``"Completed"``, etc.
        days_back:
            How many days of history to retrieve.
        """
        from datetime import timedelta
        from ebay_bot.utils import utcnow

        create_time_from = (utcnow() - timedelta(days=days_back)).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )

        try:
            response = self._trading.execute(
                "GetOrders",
                {
                    "CreateTimeFrom": create_time_from,
                    "OrderStatus": order_status,
                    "Pagination": {"EntriesPerPage": 100, "PageNumber": 1},
                },
            )
        except EbayConnectionError as exc:
            raise EbayAPIError(f"GetOrders failed: {exc}") from exc

        reply = response.reply
        order_array = getattr(reply, "OrderArray", None)
        if not order_array:
            return []

        orders = getattr(order_array, "Order", [])
        if not isinstance(orders, list):
            orders = [orders]

        logger.info("Fetched %d order(s) with status '%s'.", len(orders), order_status)
        return [o.__dict__ for o in orders]

    # ------------------------------------------------------------------
    # Inventory management
    # ------------------------------------------------------------------

    def get_item(self, item_id: str) -> dict[str, Any]:
        """Return the full item detail for a single listing."""
        try:
            response = self._trading.execute("GetItem", {"ItemID": item_id})
        except EbayConnectionError as exc:
            raise EbayAPIError(f"GetItem failed for {item_id}: {exc}") from exc

        return response.reply.Item.__dict__

    def update_quantity(self, item_id: str, quantity: int) -> None:
        """Update the available quantity of an existing listing."""
        if quantity < 0:
            raise ValueError("quantity must be >= 0")

        try:
            self._trading.execute(
                "ReviseItem",
                {
                    "Item": {
                        "ItemID": item_id,
                        "Quantity": quantity,
                    }
                },
            )
        except EbayConnectionError as exc:
            raise EbayAPIError(
                f"ReviseItem (quantity update) failed for {item_id}: {exc}"
            ) from exc

        logger.info("Updated quantity for item %s to %d.", item_id, quantity)

    def update_price(self, item_id: str, price: float) -> None:
        """Update the Buy-It-Now price of an existing listing."""
        if price <= 0:
            raise ValueError("price must be > 0")

        try:
            self._trading.execute(
                "ReviseItem",
                {
                    "Item": {
                        "ItemID": item_id,
                        "StartPrice": f"{price:.2f}",
                    }
                },
            )
        except EbayConnectionError as exc:
            raise EbayAPIError(
                f"ReviseItem (price update) failed for {item_id}: {exc}"
            ) from exc

        logger.info("Updated price for item %s to %.2f.", item_id, price)

    def relist_item(self, item_id: str) -> str:
        """Relist an ended item and return the new item ID."""
        try:
            response = self._trading.execute("RelistItem", {"Item": {"ItemID": item_id}})
        except EbayConnectionError as exc:
            raise EbayAPIError(f"RelistItem failed for {item_id}: {exc}") from exc

        new_id = response.reply.ItemID
        logger.info("Relisted item %s as new item %s.", item_id, new_id)
        return new_id

    # ------------------------------------------------------------------
    # Seller summary
    # ------------------------------------------------------------------

    def get_seller_summary(self) -> dict[str, Any]:
        """Return high-level account metrics from GetMyeBaySelling."""
        try:
            response = self._trading.execute(
                "GetMyeBaySelling",
                {
                    "SellingSummary": {"Include": True},
                },
            )
        except EbayConnectionError as exc:
            raise EbayAPIError(f"GetMyeBaySelling (summary) failed: {exc}") from exc

        summary = getattr(response.reply, "SellingSummary", None)
        if summary is None:
            return {}
        return summary.__dict__
