"""Platform for sensor integration."""
from __future__ import annotations

import logging

from collections.abc import Mapping
from datetime import timedelta, datetime
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, ICON_UPDATE, ICON_CREDIT, ICON_NO_LIMIT, ICON_FREE_EXPRESS, ICON_DELIVERY, ICON_BAGS, \
    ICON_CART, ICON_ACCOUNT, ICON_EMAIL, ICON_PHONE, ICON_PREMIUM_DAYS, ICON_LAST_ORDER, ICON_NEXT_ORDER_SINCE, \
    ICON_NEXT_ORDER_TILL
from .entity import BaseEntity
from .hub import RohlikAccount

SCAN_INTERVAL = timedelta(seconds=600)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Add sensors for passed config_entry in HA."""
    rohlik_account: RohlikAccount = hass.data[DOMAIN][config_entry.entry_id]  # type: ignore[Any]

    entities = [
        FirstDeliverySensor(rohlik_account),
        AccountIDSensor(rohlik_account),
        EmailSensor(rohlik_account),
        PhoneSensor(rohlik_account),
        NoLimitOrders(rohlik_account),
        FreeExpressOrders(rohlik_account),
        CreditAmount(rohlik_account),
        BagsAmountSensor(rohlik_account),
        CartPriceSensor(rohlik_account),
        UpdateSensor(rohlik_account),
        LastOrder(rohlik_account),
        NextOrderTill(rohlik_account),
        NextOrderSince(rohlik_account),
        FirstExpressSlot(rohlik_account),
        FirstStandardSlot(rohlik_account),
        FirstEcoSlot(rohlik_account)
    ]

    # Only add premium days remaining if the user is premium
    if rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('premium', {}).get('active', False):
        entities.append(PremiumDaysRemainingSensor(rohlik_account))

    async_add_entities(entities)

class FirstExpressSlot(BaseEntity, SensorEntity):
    """Sensor for first available delivery."""

    _attr_translation_key = "express_slot"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns datetime of the express slot."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        state = None
        for slot in preselected_slots:
            if slot.get("type", "") == "EXPRESS":
                state = datetime.strptime(slot.get("slot", {}).get("interval", {}).get("since", None),
                                          "%Y-%m-%dT%H:%M:%S%z")
                break
        return state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        extra_attrs = None
        for slot in preselected_slots:
            if slot.get("type", "") == "EXPRESS":
                extra_attrs = {
                    "Delivery Slot End": datetime.strptime(slot.get("slot", {}).get("interval", {}).get("till", None),
                                                           "%Y-%m-%dT%H:%M:%S%z"),
                    "Remaining Capacity Percent": int(
                        slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get("totalFreeCapacityPercent", 0)),
                    "Remaining Capacity Message": slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get(
                        "capacityMessage", None),
                    "Price": int(slot.get("price", 0)),
                    "Title": slot.get("title", None),
                    "Subtitle": slot.get("subtitle", None)
                }
                break

        return extra_attrs

    @property
    def entity_picture(self) -> str | None:
        return  "https://cdn.rohlik.cz/images/icons/preselected-slots/express.png"


    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class FirstStandardSlot(BaseEntity, SensorEntity):
    """Sensor for first available delivery."""

    _attr_translation_key = "standard_slot"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns datetime of the standard slot."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        state = None
        for slot in preselected_slots:
            if slot.get("type", "") == "FIRST":
                state = datetime.strptime(slot.get("slot", {}).get("interval", {}).get("since", None),
                                          "%Y-%m-%dT%H:%M:%S%z")
                break
        return state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        extra_attrs = None
        for slot in preselected_slots:
            if slot.get("type", "") == "FIRST":
                extra_attrs = {
                    "Delivery Slot End": datetime.strptime(slot.get("slot", {}).get("interval", {}).get("till", None),
                                                           "%Y-%m-%dT%H:%M:%S%z"),
                    "Remaining Capacity Percent": int(
                        slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get("totalFreeCapacityPercent", 0)),
                    "Remaining Capacity Message": slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get(
                        "capacityMessage", None),
                    "Price": int(slot.get("price", 0)),
                    "Title": slot.get("title", None),
                    "Subtitle": slot.get("subtitle", None)
                    }
                break

        return extra_attrs

    @property
    def entity_picture(self) -> str | None:
        return  "https://cdn.rohlik.cz/images/icons/preselected-slots/first.png"

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class FirstEcoSlot(BaseEntity, SensorEntity):
    """Sensor for first available delivery."""

    _attr_translation_key = "eco_slot"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns datetime of the eco slot."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        state = None
        for slot in preselected_slots:
            if slot.get("type", "") == "ECO":
                state = datetime.strptime(slot.get("slot", {}).get("interval", {}).get("since", None), "%Y-%m-%dT%H:%M:%S%z")
                break
        return state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = self._rohlik_account.data["next_delivery_slot"].get('data', {}).get('preselectedSlots', [])
        extra_attrs = None
        for slot in preselected_slots:
            if slot.get("type", "") == "ECO":
                extra_attrs = {"Delivery Slot End": datetime.strptime(slot.get("slot", {}).get("interval", {}).get("till", None), "%Y-%m-%dT%H:%M:%S%z"),
                    "Remaining Capacity Percent": int(slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get("totalFreeCapacityPercent", 0)),
                    "Remaining Capacity Message": slot.get("slot", {}).get("timeSlotCapacityDTO", {}).get("capacityMessage", None),
                    "Price": int(slot.get("price", 0)),
                    "Title": slot.get("title", None),
                    "Subtitle": slot.get("subtitle", None)
                    }
                break

        return extra_attrs

    @property
    def entity_picture(self) -> str | None:
        return  "https://cdn.rohlik.cz/images/icons/preselected-slots/eco.png"

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class FirstDeliverySensor(BaseEntity, SensorEntity):
    """Sensor for first available delivery."""

    _attr_translation_key = "first_delivery"
    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Returns first available delivery time."""
        return self._rohlik_account.data.get('delivery', {}).get('data', {}).get('firstDeliveryText', {}).get('default', 'Unknown')

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns delivery location."""
        delivery_data = self._rohlik_account.data.get('delivery', {}).get('data', {})
        if delivery_data:
            return {
                "delivery_location": delivery_data.get('deliveryLocationText', ''),
                "delivery_type": delivery_data.get('deliveryType', '')
            }
        return None

    @property
    def icon(self) -> str:
        return ICON_DELIVERY

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class AccountIDSensor(BaseEntity, SensorEntity):
    """Sensor for account ID."""

    _attr_translation_key = "account_id"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def native_value(self) -> int | str:
        """Returns account ID."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('id', "N/A")

    @property
    def icon(self) -> str:
        return ICON_ACCOUNT

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class EmailSensor(BaseEntity, SensorEntity):
    """Sensor for email."""

    _attr_translation_key = "email"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Returns email."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('email', 'N/A')

    @property
    def icon(self) -> str:
        return ICON_EMAIL

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class PhoneSensor(BaseEntity, SensorEntity):
    """Sensor for phone number."""

    _attr_translation_key = "phone"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False

    @property
    def native_value(self) -> str:
        """Returns phone number."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('phone', 'N/A')

    @property
    def icon(self) -> str:
        return ICON_PHONE

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class CreditAmount(BaseEntity, SensorEntity):
    """Sensor for credit amount."""

    _attr_translation_key = "credit_amount"
    _attr_should_poll = False

    @property
    def native_value(self) -> float | str:
        """Returns amount of credit as state."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('credits', "N/A")

    @property
    def icon(self) -> str:
        return ICON_CREDIT

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class NoLimitOrders(BaseEntity, SensorEntity):
    """Sensor for remaining no limit orders."""

    _attr_translation_key = "no_limit"
    _attr_should_poll = False

    @property
    def native_value(self) -> int:
        """Returns remaining orders without limit."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('premium', {}).get('premiumLimits', {}).get('ordersWithoutPriceLimit', {}).get('remaining', 0)

    @property
    def icon(self) -> str:
        return ICON_NO_LIMIT

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class FreeExpressOrders(BaseEntity, SensorEntity):
    """Sensor for remaining free express orders."""

    _attr_translation_key = "free_express"
    _attr_should_poll = False

    @property
    def native_value(self) -> int:
        """Returns remaining free express orders."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('premium', {}).get('premiumLimits', {}).get('freeExpressLimit', {}).get('remaining', 0)

    @property
    def icon(self) -> str:
        return ICON_FREE_EXPRESS

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class BagsAmountSensor(BaseEntity, SensorEntity):
    """Sensor for reusable bags amount."""

    _attr_translation_key = "bags_amount"
    _attr_should_poll = False

    @property
    def native_value(self) -> int:
        """Returns number of reusable bags."""
        return self._rohlik_account.data["bags"].get('current', 0)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns reusable bag details."""
        bags_data = self._rohlik_account.data["bags"]
        extra_attr: dict = {"Max Bags": bags_data.get('max', 0)}
        if bags_data.get('deposit', None):
            extra_attr["Deposit Amount"] = bags_data.get('deposit').get('amount', 0)
            extra_attr["Deposit Currency"] = bags_data.get('deposit').get('currency', 'CZK')
        return extra_attr

    @property
    def icon(self) -> str:
        return ICON_BAGS

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class PremiumDaysRemainingSensor(BaseEntity, SensorEntity):
    """Sensor for premium days remaining."""

    _attr_translation_key = "premium_days"
    _attr_should_poll = False

    @property
    def native_value(self) -> int:
        """Returns premium days remaining."""
        return self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('premium', {}).get('remainingDays', 0)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns premium details."""
        premium_data = self._rohlik_account.data.get('login', {}).get('data', {}).get('user', {}).get('premium', {})
        if premium_data:
            return {
                "Premium Type": premium_data.get('premiumMembershipType', ''),
                "Payment Date": premium_data.get('recurrentPaymentDate', ''),
                "Start Date": premium_data.get('startDate', ''),
                "End Date": premium_data.get('endDate', '')
            }
        return None

    @property
    def icon(self) -> str:
        return ICON_PREMIUM_DAYS

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class CartPriceSensor(BaseEntity, SensorEntity):
    """Sensor for total cart price."""

    _attr_translation_key = "cart_price"
    _attr_should_poll = False

    @property
    def native_value(self) -> float:
        """Returns total cart price."""
        return self._rohlik_account.data.get('cart', {}).get('data', {}).get('totalPrice', 0.0)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns cart details."""
        cart_data = self._rohlik_account.data.get('cart', {}).get('data', {})
        if cart_data:
            return {
                "Total savings": cart_data.get('totalSavings', 0),
                "Minimal Order Price": cart_data.get('minimalOrderPrice', 0),
                "Can Order": cart_data.get('submitConditionPassed', False)
            }
        return None

    @property
    def icon(self) -> str:
        return ICON_CART

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)

class NextOrderSince(BaseEntity, SensorEntity):
    """Sensor for start of delivery window of next order."""

    _attr_translation_key = "next_order_since"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns remaining orders without limit."""
        if len(self._rohlik_account.data['next_order']) > 0:
            slot_start = datetime.strptime(self._rohlik_account.data["next_order"][0].get("deliverySlot", {}).get("since", None),
                                 "%Y-%m-%dT%H:%M:%S.%f%z")
            return slot_start
        else:
            return None

    @property
    def icon(self) -> str:
        return ICON_NEXT_ORDER_SINCE

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)

class NextOrderTill(BaseEntity, SensorEntity):
    """Sensor for finish of delivery window of next order."""

    _attr_translation_key = "next_order_till"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns remaining orders without limit."""
        if len(self._rohlik_account.data['next_order']) > 0:
            slot_start = datetime.strptime(self._rohlik_account.data["next_order"][0].get("deliverySlot", {}).get("till", None),
                                 "%Y-%m-%dT%H:%M:%S.%f%z")
            return slot_start
        else:
            return None

    @property
    def icon(self) -> str:
        return ICON_NEXT_ORDER_TILL

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class LastOrder(BaseEntity, SensorEntity):
    """Sensor for datetime from last order."""

    _attr_translation_key = "last_order"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime:
        """Returns remaining orders without limit."""
        return datetime.strptime(self._rohlik_account.data["last_order"][0].get("orderTime", None), "%Y-%m-%dT%H:%M:%S.%f%z")

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns last order details."""
        last_order_data = self._rohlik_account.data['last_order'][0]
        if len(last_order_data) > 0:
            return {
                "Items": last_order_data.get('itemsCount', None),
                "Price": last_order_data.get('priceComposition', {}).get('total', {}).get('amount', None),
            }
        return None


    @property
    def icon(self) -> str:
        return ICON_LAST_ORDER

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class UpdateSensor(BaseEntity, SensorEntity):
    """Sensor for API update."""

    _attr_translation_key = "updated"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = ICON_UPDATE
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, rohlik_account: RohlikAccount) -> None:
        super().__init__(rohlik_account)
        self._attr_native_value = datetime.now(tz=ZoneInfo("Europe/Prague"))

    async def async_update(self) -> None:
        """Calls regular update of data from API."""
        await self._rohlik_account.async_update()
        self._attr_native_value = datetime.now(tz=ZoneInfo("Europe/Prague"))
