"""Platform for binary sensor."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ICON_PREMIUM, ICON_PARENTCLUB
from .entity import BaseEntity
from .hub import RohlikAccount

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Add sensors for passed config_entry in HA."""
    rohlik_account: RohlikAccount = hass.data[DOMAIN][config_entry.entry_id]  # type: ignore[Any]
    async_add_entities([IsPremiumSensor(rohlik_account), IsParentSensor(rohlik_account)])


class IsPremiumSensor(BaseEntity, BinarySensorEntity):
    """Sensor for premium account."""

    _attr_translation_key = "is_premium"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        if self._rohlik_account.is_premium == "true":
            return True
        elif self._rohlik_account.is_premium == "false":
            return False
        else:
            return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        return None

    @property
    def icon(self) -> str:
        return ICON_PREMIUM

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsParentSensor(BaseEntity, BinarySensorEntity):
    """Sensor for wheelchair accessibility of the station."""

    _attr_translation_key = "is_parent"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        if self._rohlik_account.is_parent == "true":
            return True
        elif self._rohlik_account.is_parent == "false":
            return False
        else:
            return None

    @property
    def icon(self) -> str:
        return ICON_PARENTCLUB

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class NextOrderMade(BaseEntity, BinarySensorEntity):
    """Sensor for whether the order is currently made."""

    _attr_translation_key = "is_ordered"
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        if self._rohlik_account.is_parent == "true":
            return True
        elif self._rohlik_account.is_parent == "false":
            return False
        else:
            return None

    @property
    def icon(self) -> str:
        return ICON_PARENTCLUB

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)