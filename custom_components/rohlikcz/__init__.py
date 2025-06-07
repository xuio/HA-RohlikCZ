"""Rohlík CZ custom component."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_BASE_URL
from .hub import RohlikAccount
from .services import register_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor", "todo"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Rohlik integration from a config entry flow."""
    # Support older config entries that may not have base_url stored
    base_url: str = entry.data.get(CONF_BASE_URL, "https://www.rohlik.cz")

    rohlik_hub = RohlikAccount(
        hass,
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
        base_url,
    )
    await rohlik_hub.async_update()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = rohlik_hub

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
