"""Platform for sensor integration."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta, datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import BaseEntity
from .hub import RohlikAccount

SCAN_INTERVAL = timedelta(seconds=300)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Add sensors for passed config_entry in HA."""
    rohlik_account: RohlikAccount = hass.data[DOMAIN][config_entry.entry_id]  # type: ignore[Any]
    async_add_entities([CreditAmount(rohlik_account)])


class CreditAmount(BaseEntity, SensorEntity):
    """Sensor for credit amount."""

    _attr_translation_key = "credit_amount"
    _attr_should_poll = False

    def __init__(self, rohlik_account: RohlikAccount) -> None:
        super().__init__(rohlik_account)
        self._attr_unique_id = f"{rohlik_account.user_id}_{self.translation_key}"

    @property
    def native_value(self) -> int:
        """ Returns amount of credit as state."""
        return self._rohlik_account.credit_amount

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """ Returns dictionary of additional state attributes"""
        pass

    @property
    def icon(self) -> str:
        """Returns entity icon based on the type of route"""
        return None

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)
