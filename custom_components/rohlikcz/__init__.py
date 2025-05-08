"""Rohlík CZ custom component."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .hub import RohlikAccount
from .services import register_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor"]

# Define service constants
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_PRODUCT_ID = "product_id"
ATTR_QUANTITY = "quantity"
ATTR_PRODUCT_NAME = "product_name"
ATTR_SHOPPING_LIST_ID = "shopping_list_id"

# Define service names
SERVICE_ADD_TO_CART = "add_to_cart"
SERVICE_SEARCH_PRODUCT = "search_product"
SERVICE_GET_SHOPPING_LIST = "get_shopping_list"
SERVICE_GET_CART_CONTENT = "get_cart_content"
SERVICE_SEARCH_AND_ADD_PRODUCT = "search_and_add_to_cart"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rohlik integration from a config entry flow."""
    account = RohlikAccount(hass, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])
    await account.async_update()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = account

    # Register services
    register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


