"""Platform for binary sensor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    ICON_REUSABLE,
    ICON_PARENTCLUB,
    ICON_PREMIUM,
    ICON_ORDER,
    ICON_TIMESLOT,
    ICON_CALENDAR_CHECK,
    ICON_CALENDAR_REMOVE,
)
from .entity import BaseEntity
from .hub import RohlikAccount


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    rohlik_account: RohlikAccount = hass.data[DOMAIN][config_entry.entry_id]  # type: ignore[Any]
    entities = [
        IsReusableSensor(rohlik_account),
        IsParentSensor(rohlik_account),
        IsPremiumSensor(rohlik_account),
        IsOrderedSensor(rohlik_account),
        IsReservedSensor(rohlik_account),
    ]

    # Express availability is relevant only for rohlik.cz
    if not rohlik_account.is_knuspr:
        entities.append(IsExpressAvailable(rohlik_account))

    async_add_entities(entities)


class IsExpressAvailable(BaseEntity, BinarySensorEntity):
    _attr_translation_key = "is_express_available"
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        if (
            not self._rohlik_account.data["next_delivery_slot"]
            .get("data", {})
            .get("expressSlot", None)
        ):
            return False
        elif (
            int(
                self._rohlik_account.data["next_delivery_slot"]
                .get("data", {})
                .get("expressSlot", {})
                .get("timeSlotCapacityDTO", {})
                .get("totalFreeCapacityPercent", 0)
            )
            == 0
        ):
            return False
        else:
            return True

    @property
    def icon(self) -> str:
        if self.is_on:
            return ICON_CALENDAR_CHECK
        else:
            return ICON_CALENDAR_REMOVE

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsReusableSensor(BaseEntity, BinarySensorEntity):
    """Sensor to say whether the user use reusable bags."""

    _attr_translation_key = "is_reusable"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("reusablePackaging", False)
        )

    @property
    def icon(self) -> str:
        return ICON_REUSABLE

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        # Sensors should also register callbacks to HA when their state changes
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        # The opposite of async_added_to_hass. Remove any registered call backs here.
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsParentSensor(BaseEntity, BinarySensorEntity):
    """Sensor for whether the user is a member of the parent club."""

    _attr_translation_key = "is_parent"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("parentsClub", False)
        )

    @property
    def icon(self) -> str:
        return ICON_PARENTCLUB

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsPremiumSensor(BaseEntity, BinarySensorEntity):
    """Sensor for whether the user has premium membership."""

    _attr_translation_key = "is_premium"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
            .get("active", False)
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        premium_data = (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
        )
        if premium_data:
            return {
                "type": premium_data.get("premiumMembershipType"),
                "payment_type": premium_data.get("premiumType"),
                "expiration_date": premium_data.get("recurrentPaymentDate"),
                "remaining_days": premium_data.get("remainingDays"),
                "start_date": premium_data.get("startDate"),
                "end_date": premium_data.get("endDate"),
                "remaining_orders_without_limit": premium_data.get("premiumLimits", {})
                .get("ordersWithoutPriceLimit", {})
                .get("remaining"),
                "remaining_free_express": premium_data.get("premiumLimits", {})
                .get("freeExpressLimit", {})
                .get("remaining"),
            }
        return None

    @property
    def icon(self) -> str:
        return ICON_PREMIUM

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsOrderedSensor(BaseEntity, BinarySensorEntity):
    """Sensor for whether the next order is scheduled."""

    _attr_translation_key = "is_ordered"
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        # Check if there's at least one order in the next_order list
        return len(self._rohlik_account.data.get("next_order", [])) > 0

    @property
    def extra_state_attributes(self) -> dict | None:
        next_orders = self._rohlik_account.data.get("next_order", [])
        if next_orders and len(next_orders) > 0:
            order = next_orders[0]  # Get the first next order
            return {"order_data": order}
        return None

    @property
    def icon(self) -> str:
        return ICON_ORDER

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class IsReservedSensor(BaseEntity, BinarySensorEntity):
    """Sensor for whether a timeslot is reserved."""

    _attr_translation_key = "is_reserved"
    _attr_should_poll = False

    @property
    def is_on(self) -> bool | None:
        return (
            self._rohlik_account.data.get("timeslot", {})
            .get("data", {})
            .get("active", False)
        )

    @property
    def extra_state_attributes(self) -> dict | None:
        timeslot_data = (
            self._rohlik_account.data.get("timeslot", {})
            .get("data", {})
            .get("reservationDetail", {})
        )
        if timeslot_data:
            return timeslot_data
        return None

    @property
    def icon(self) -> str:
        return ICON_TIMESLOT

    async def async_added_to_hass(self) -> None:
        """Run when this Entity has been added to HA."""
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        """Entity being removed from hass."""
        self._rohlik_account.remove_callback(self.async_write_ha_state)
