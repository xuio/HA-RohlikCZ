"""Todo platform for Rohlik.cz integration."""

from __future__ import annotations

import logging
import re

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, ICON_CART
from .hub import RohlikAccount

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Rohlik shopping cart todo platform config entry."""
    rohlik_hub = hass.data[DOMAIN][config_entry.entry_id]

    async_add_entities([RohlikCartTodo(rohlik_hub)])


class RohlikCartTodo(TodoListEntity):
    """A Rohlik Shopping Cart TodoListEntity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )
    _attr_translation_key = "shopping_cart"
    _attr_icon = ICON_CART

    def __init__(self, rohlik_hub: RohlikAccount) -> None:
        """Initialize RohlikCartTodo."""
        super().__init__()
        self._rohlik_hub = rohlik_hub
        self._attr_unique_id = f"{rohlik_hub.unique_id}-cart"
        self._attr_name = (
            "Knuspr Shopping Cart" if rohlik_hub.is_knuspr else "Rohlik Shopping Cart"
        )
        self._attr_device_info = rohlik_hub.device_info
        self._cart_content = None

        # Register callback for updates
        rohlik_hub.register_callback(self.async_write_ha_state)

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Handle updated data from the hub."""
        self._cart_content = self._rohlik_hub.data["cart"]

        if not self._cart_content:
            return None

        items = []
        for product in self._cart_content.get("products", []):
            # Format the summary to include relevant information
            currency_symbol = "€" if self._rohlik_hub.is_knuspr else "Kč"
            summary = f"{product['name']} ({product['quantity']}) - {product['price']} {currency_symbol}"

            # Use cart_item_id as the unique identifier for cart items
            items.append(
                TodoItem(
                    summary=summary,
                    uid=str(product["cart_item_id"]),
                    status=TodoItemStatus.NEEDS_ACTION,
                    description=f"Category: {product.get('category_name', '')}\n"
                    f"Brand: {product.get('brand', '')}\n"
                    f"Product ID: {product['id']}",
                )
            )

        return items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add item to shopping cart.

        Supports two input formats:
        - "product name" (quantity defaults to 1)
        - "X product name" (where X is the desired quantity)
        """

        # Check if the summary starts with a number followed by a space
        quantity_match = re.match(r"^(\d+)\s+(.+)$", item.summary)

        if quantity_match:
            # If format is "X product name"
            quantity = int(quantity_match.group(1))
            product_name = quantity_match.group(2)
        else:
            # If format is just "product name"
            quantity = 1
            product_name = item.summary

        # If there's still quantity info in parentheses, use that instead This handles cases like "rohlík (3)" or "2 rohlíky (5)" where (5) would take precedence
        parentheses_match = re.search(r"\((\d+)\)$", product_name)
        if parentheses_match:
            quantity = int(parentheses_match.group(1))
            product_name = product_name.split("(")[0].strip()

        # Search for product and add to cart
        result = await self._rohlik_hub.search_and_add(product_name, quantity)

        if not result or not result.get("success", False):
            _LOGGER.error("Error with adding product to")
            raise ServiceValidationError(f"Product not found: {product_name}")

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items from the shopping cart using the dedicated delete endpoint."""
        for uid in uids:
            try:
                # Call the new delete_from_cart method with the cart_item_id
                await self._rohlik_hub.delete_from_cart(uid)
                _LOGGER.error(f"Deleted item: {uid}")
            except Exception as err:
                _LOGGER.error("Error deleting item %s: %s", uid, err)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an item to the To-do list."""
        pass
