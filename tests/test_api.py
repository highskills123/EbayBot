"""Tests for EbayAPI (api.py) – mocks the ebaysdk connections."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ebay_bot.api import EbayAPI, EbayAPIError
from ebay_bot.config import Config


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_config(monkeypatch):
    monkeypatch.setenv("EBAY_APP_ID", "app")
    monkeypatch.setenv("EBAY_DEV_ID", "dev")
    monkeypatch.setenv("EBAY_CERT_ID", "cert")
    monkeypatch.setenv("EBAY_USER_TOKEN", "token")
    monkeypatch.setenv("EBAY_SANDBOX", "True")
    return Config()


@pytest.fixture()
def api(mock_config):
    """Return an EbayAPI whose SDK connections are fully mocked."""
    with patch("ebay_bot.api.Trading") as MockTrading, \
         patch("ebay_bot.api.Finding") as MockFinding:
        instance = EbayAPI(mock_config)
        instance._trading = MockTrading.return_value
        instance._finding = MockFinding.return_value
        yield instance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item(item_id="100", title="Test Item", qty=10):
    return SimpleNamespace(ItemID=item_id, Title=title, QuantityAvailable=str(qty),
                           __dict__={"ItemID": item_id, "Title": title,
                                     "QuantityAvailable": str(qty)})


def _active_list_response(items):
    item_array = SimpleNamespace(Item=items)
    pagination = SimpleNamespace(TotalNumberOfPages="1")
    active_list = SimpleNamespace(ItemArray=item_array, PaginationResult=pagination)
    return SimpleNamespace(reply=SimpleNamespace(ActiveList=active_list))


# ---------------------------------------------------------------------------
# get_active_listings
# ---------------------------------------------------------------------------


def test_get_active_listings_returns_items(api):
    items = [_item("1"), _item("2")]
    api._trading.execute.return_value = _active_list_response(items)
    result = api.get_active_listings()
    assert len(result) == 2
    assert result[0]["ItemID"] == "1"


def test_get_active_listings_single_item(api):
    """When the API returns a single item (not a list) it should still work."""
    api._trading.execute.return_value = _active_list_response(_item("99"))
    result = api.get_active_listings()
    assert len(result) == 1


def test_get_active_listings_raises_on_connection_error(api):
    from ebaysdk.exception import ConnectionError as EbayConnectionError
    api._trading.execute.side_effect = EbayConnectionError("timeout")
    with pytest.raises(EbayAPIError):
        api.get_active_listings()


# ---------------------------------------------------------------------------
# get_orders
# ---------------------------------------------------------------------------


def test_get_orders_returns_orders(api):
    order = SimpleNamespace(OrderID="ORD1", OrderStatus="Active",
                            __dict__={"OrderID": "ORD1", "OrderStatus": "Active"})
    order_array = SimpleNamespace(Order=[order])
    api._trading.execute.return_value = SimpleNamespace(
        reply=SimpleNamespace(OrderArray=order_array)
    )
    orders = api.get_orders()
    assert len(orders) == 1
    assert orders[0]["OrderID"] == "ORD1"


def test_get_orders_empty(api):
    api._trading.execute.return_value = SimpleNamespace(
        reply=SimpleNamespace(OrderArray=None)
    )
    assert api.get_orders() == []


# ---------------------------------------------------------------------------
# update_quantity
# ---------------------------------------------------------------------------


def test_update_quantity_calls_revise(api):
    api._trading.execute.return_value = MagicMock()
    api.update_quantity("ITEM1", 5)
    call_args = api._trading.execute.call_args
    assert call_args[0][0] == "ReviseItem"
    assert call_args[0][1]["Item"]["ItemID"] == "ITEM1"
    assert call_args[0][1]["Item"]["Quantity"] == 5


def test_update_quantity_rejects_negative(api):
    with pytest.raises(ValueError):
        api.update_quantity("ITEM1", -1)


# ---------------------------------------------------------------------------
# update_price
# ---------------------------------------------------------------------------


def test_update_price_calls_revise(api):
    api._trading.execute.return_value = MagicMock()
    api.update_price("ITEM1", 29.99)
    call_args = api._trading.execute.call_args
    assert call_args[0][0] == "ReviseItem"
    assert call_args[0][1]["Item"]["StartPrice"] == "29.99"


def test_update_price_rejects_zero(api):
    with pytest.raises(ValueError):
        api.update_price("ITEM1", 0)


# ---------------------------------------------------------------------------
# relist_item
# ---------------------------------------------------------------------------


def test_relist_item_returns_new_id(api):
    api._trading.execute.return_value = SimpleNamespace(
        reply=SimpleNamespace(ItemID="NEW999")
    )
    new_id = api.relist_item("OLD1")
    assert new_id == "NEW999"


# ---------------------------------------------------------------------------
# get_seller_summary
# ---------------------------------------------------------------------------


def test_get_seller_summary_returns_dict(api):
    summary = SimpleNamespace(ActiveListingCount="3",
                              __dict__={"ActiveListingCount": "3"})
    api._trading.execute.return_value = SimpleNamespace(
        reply=SimpleNamespace(SellingSummary=summary)
    )
    result = api.get_seller_summary()
    assert result["ActiveListingCount"] == "3"


def test_get_seller_summary_empty_when_no_summary(api):
    api._trading.execute.return_value = SimpleNamespace(
        reply=SimpleNamespace(SellingSummary=None)
    )
    assert api.get_seller_summary() == {}
