"""Platform for sensor integration."""

from __future__ import annotations

import logging
import re
import datetime

from collections.abc import Mapping
from datetime import timedelta, datetime, time
from typing import Any, Callable
from zoneinfo import ZoneInfo
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util
from .const import (
    DOMAIN,
    ICON_UPDATE,
    ICON_CREDIT,
    ICON_NO_LIMIT,
    ICON_FREE_EXPRESS,
    ICON_DELIVERY,
    ICON_BAGS,
    ICON_CART,
    ICON_ACCOUNT,
    ICON_EMAIL,
    ICON_PHONE,
    ICON_PREMIUM_DAYS,
    ICON_LAST_ORDER,
    ICON_NEXT_ORDER_SINCE,
    ICON_NEXT_ORDER_TILL,
    ICON_INFO,
)
from .entity import BaseEntity
from .hub import RohlikAccount

SCAN_INTERVAL = timedelta(seconds=600)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    rohlik_hub: RohlikAccount = hass.data[DOMAIN][config_entry.entry_id]  # type: ignore[Any]

    entities = [
        FirstDeliverySensor(rohlik_hub),
        ParsedDeliveryTimeSensor(rohlik_hub),
        NextOrderIDSensor(rohlik_hub),
        AccountIDSensor(rohlik_hub),
        EmailSensor(rohlik_hub),
        PhoneSensor(rohlik_hub),
        NoLimitOrders(rohlik_hub),
        # Free Express deliveries are a Czech premium feature, hide on Knuspr
        *([] if rohlik_hub.is_knuspr else [FreeExpressOrders(rohlik_hub)]),
        CreditAmount(rohlik_hub),
        BagsAmountSensor(rohlik_hub),
        CartPriceSensor(rohlik_hub),
        UpdateSensor(rohlik_hub),
        LastOrder(rohlik_hub),
        NextOrderTill(rohlik_hub),
        NextOrderSince(rohlik_hub),
        DeliveryInfo(rohlik_hub),
    ]

    # Add delivery slot sensors depending on site capabilities
    if rohlik_hub.has_address:
        # Knuspr does not support these slot types
        if not rohlik_hub.is_knuspr:
            entities.append(FirstExpressSlot(rohlik_hub))
            entities.append(FirstEcoSlot(rohlik_hub))
            entities.append(FirstStandardSlot(rohlik_hub))

    # Only add premium days remaining if the user is premium
    if (
        rohlik_hub.data.get("login", {})
        .get("data", {})
        .get("user", {})
        .get("premium", {})
        .get("active", False)
    ):
        entities.append(PremiumDaysRemainingSensor(rohlik_hub))

    async_add_entities(entities)


class DeliveryInfo(BaseEntity, SensorEntity):
    """Sensor for showing delivery information."""

    _attr_translation_key = "delivery_info"
    _attr_should_poll = False

    @property
    def native_value(self) -> str | None:
        """Returns text of announcement."""
        delivery_info: list = self._rohlik_account.data["delivery_announcements"][
            "data"
        ]["announcements"]
        if len(delivery_info) > 0:
            clean_text = re.sub(r"<[^>]+>", "", delivery_info[0]["content"])
            return clean_text
        else:
            return None

    @staticmethod
    def extract_delivery_datetime(
        text: str, is_knuspr: bool = False
    ) -> datetime | None:
        """
        Extract delivery time information from various formatted strings and return a datetime object.

        Handles three types of delivery messages:
        1. Time only (HH:MM): "delivery at 17:23"
        2. Date and time: "delivery on 26.4. at 08:00"
        3. Minutes until delivery: "delivery in approximately 3 minutes"

        Args:
            text: HTML text containing delivery time information
            is_knuspr: Flag indicating if the shop is Knuspr

        Returns:
            A timezone-aware datetime object representing the delivery time, or None if no valid time found
        """

        # Replace Unicode escape sequences
        clean_text: str = text.encode("utf-8").decode("unicode_escape")

        # Get plain text without HTML tags for pattern detection
        plain_text: str = re.sub(r"<[^>]+>", "", clean_text)

        # Determine timezone based on shop variant (Rohlík vs. Knuspr)
        tz = ZoneInfo("Europe/Berlin") if is_knuspr else ZoneInfo("Europe/Prague")

        now = datetime.now(tz=tz)
        current_year: int = now.year

        # -------------- TYPE 3: "in X minutes" -----------------
        # Look for a number followed by a minutes keyword (CZ or DE variants)
        _minutes_keyword_re = r"minut|minuty|min|Minuten|Min\\.?|Min"

        # First try to grab highlighted numbers inside <span> tags
        minutes_span_pattern = re.compile(
            r"<span[^>]*>([0-9]{1,3})</span>\s*(?:" + _minutes_keyword_re + ")",
            re.IGNORECASE,
        )
        span_match = minutes_span_pattern.search(clean_text)
        if span_match:
            try:
                return now + timedelta(minutes=int(span_match.group(1)))
            except ValueError:
                pass

        # Fallback to plain-text detection like "in 55 Minuten", "in etwa 3 Minuten"
        plain_minutes_match = re.search(
            r"\b([0-9]{1,3})\s*(?:" + _minutes_keyword_re + ")\b",
            plain_text,
            re.IGNORECASE,
        )
        if plain_minutes_match:
            try:
                return now + timedelta(minutes=int(plain_minutes_match.group(1)))
            except ValueError:
                pass

        # -------------- Additional German date/time patterns --------------
        if is_knuspr:
            # Pattern: "am 26.4. um 08:00" OR "am 26.4. gegen 08:00" (optional ca.)
            de_date_time = re.search(
                r"am\s*([0-9]{1,2})\.\s*([0-9]{1,2})\.\s*(?:um|gegen)\s*(?:ca\.\s*)?([0-9]{1,2}:[0-9]{2})",
                plain_text,
                re.IGNORECASE,
            )
            if de_date_time:
                day = int(de_date_time.group(1))
                month = int(de_date_time.group(2))
                hour, minute = map(int, de_date_time.group(3).split(":"))
                try:
                    return datetime(current_year, month, day, hour, minute, tzinfo=tz)
                except ValueError:
                    pass

            # Only time with "gegen" / "um ca." without explicit date (today/tomorrow determination)
            de_time_only = re.search(
                r"(?:gegen|um)\s*(?:ca\.\s*)?([0-9]{1,2}:[0-9]{2})",
                plain_text,
                re.IGNORECASE,
            )
            if de_time_only:
                time_matches = [de_time_only.group(1)]

        # Check for Type 2: Date and time
        date_pattern = re.compile(
            r"<span[^>]*color:[^>]*>([0-9]{1,2}\.[0-9]{1,2}\.)</span>"
        )
        time_pattern = re.compile(r"<span[^>]*color:[^>]*>([0-9]{1,2}:[0-9]{2})</span>")

        matches_date = re.finditer(date_pattern, clean_text)
        date_matches = [match.group(1) for match in matches_date]

        matches_time = re.finditer(time_pattern, clean_text)
        time_matches = [match.group(1) for match in matches_time]

        if date_matches and time_matches:
            # We have both date and time
            try:
                date_str: str = date_matches[0]  # e.g., "26.4."
                day, month = map(int, date_str.replace(".", " ").split())

                time_str: str = time_matches[0]  # e.g., "08:00"
                hour, minute = map(int, time_str.split(":"))

                # Create full delivery datetime
                delivery_dt = datetime(
                    current_year, month, day, hour, minute, tzinfo=tz
                )

                return delivery_dt
            except (ValueError, IndexError):
                pass

        # -------------- TYPE 1: Time only --------------
        if time_matches:
            try:
                time_str: str = time_matches[0]  # e.g., "17:23"
                hour, minute = map(int, time_str.split(":"))

                # Use today's date with the specified time
                today = now.date()

                # If the time has already passed today, it might refer to tomorrow
                delivery_dt = datetime.combine(today, time(hour, minute))
                delivery_dt = delivery_dt.replace(tzinfo=tz)

                if delivery_dt < now:
                    # Time already passed today, assume it's for tomorrow
                    tomorrow = today + timedelta(days=1)
                    delivery_dt = datetime.combine(tomorrow, time(hour, minute))
                    delivery_dt = delivery_dt.replace(tzinfo=tz)

                return delivery_dt
            except (ValueError, IndexError):
                pass

        # If no structured time information was found, try to extract any time mention
        # Generic time pattern search in the plain text
        plain_time_matches = re.findall(r"\b([0-9]{1,2}:[0-9]{2})\b", plain_text)
        if plain_time_matches:
            try:
                time_str: str = plain_time_matches[0]
                hour, minute = map(int, time_str.split(":"))

                # Use today's date with the specified time
                today = now.date()

                delivery_dt = datetime.combine(today, time(hour, minute))
                delivery_dt = delivery_dt.replace(tzinfo=tz)

                # If the time has already passed today, it might refer to tomorrow
                if delivery_dt < now:
                    tomorrow = today + timedelta(days=1)
                    delivery_dt = datetime.combine(tomorrow, time(hour, minute))
                    delivery_dt = delivery_dt.replace(tzinfo=tz)

                return delivery_dt
            except (ValueError, IndexError):
                pass

        # No valid time information found
        return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Get extra state attributes."""
        delivery_info: list = self._rohlik_account.data["delivery_announcements"][
            "data"
        ]["announcements"]
        if len(delivery_info) > 0:
            delivery_time = self.extract_delivery_datetime(
                delivery_info[0].get("content", ""),
                self._rohlik_account.is_knuspr,
            )

            if delivery_info[0].get("additionalContent", None):
                clean_text = delivery_info[0]["additionalContent"]
                additional_info = re.sub(r"<[^>]+>", "", clean_text)
            else:
                additional_info = None

            return {
                "Delivery time - experimental": delivery_time,
                "Order Id": str(delivery_info[0].get("id")),
                "Updated At": datetime.fromisoformat(delivery_info[0].get("updatedAt")),
                "Title": delivery_info[0].get("title"),
                "Additional Content": additional_info,
            }

        else:
            return None

    @property
    def icon(self) -> str:
        return ICON_INFO

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class FirstExpressSlot(BaseEntity, SensorEntity):
    """Sensor for first available delivery."""

    _attr_translation_key = "express_slot"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Returns datetime of the express slot."""
        preselected_slots = (
            self._rohlik_account.data["next_delivery_slot"]
            .get("data", {})
            .get("preselectedSlots", [])
        )
        state = None
        for slot in preselected_slots:
            if slot.get("type", "") == "EXPRESS":
                state = datetime.strptime(
                    slot.get("slot", {}).get("interval", {}).get("since", None),
                    "%Y-%m-%dT%H:%M:%S%z",
                )
                break
        return state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = (
            self._rohlik_account.data["next_delivery_slot"]
            .get("data", {})
            .get("preselectedSlots", [])
        )
        extra_attrs = None
        for slot in preselected_slots:
            if slot.get("type", "") == "EXPRESS":
                extra_attrs = {
                    "Delivery Slot End": datetime.strptime(
                        slot.get("slot", {}).get("interval", {}).get("till", None),
                        "%Y-%m-%dT%H:%M:%S%z",
                    ),
                    "Remaining Capacity Percent": int(
                        slot.get("slot", {})
                        .get("timeSlotCapacityDTO", {})
                        .get("totalFreeCapacityPercent", 0)
                    ),
                    "Remaining Capacity Message": slot.get("slot", {})
                    .get("timeSlotCapacityDTO", {})
                    .get("capacityMessage", None),
                    "Price": int(slot.get("price", 0)),
                    "Title": slot.get("title", None),
                    "Subtitle": slot.get("subtitle", None),
                }
                break

        return extra_attrs

    @property
    def entity_picture(self) -> str | None:
        return "https://cdn.rohlik.cz/images/icons/preselected-slots/express.png"

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
        preselected_slots = (
            self._rohlik_account.data.get("next_delivery_slot", {})
            .get("data", {})
            .get("preselectedSlots", [])
        )

        # Try multiple type fallbacks in order of preference
        preferred_types = ["FIRST", "FIRST_CHEAPEST", "RECOMMENDED"]

        slot_candidate = None

        for ptype in preferred_types:
            for slot in preselected_slots:
                if slot.get("type", "") == ptype:
                    slot_candidate = slot
                    break
            if slot_candidate:
                break

        # If no preferred types matched, take the first slot with a proper interval
        if slot_candidate is None and len(preselected_slots) > 0:
            slot_candidate = preselected_slots[0]

        if slot_candidate:
            since_str = slot_candidate.get("slot", {}).get("interval", {}).get("since")
            if since_str:
                try:
                    return datetime.strptime(since_str, "%Y-%m-%dT%H:%M:%S%z")
                except ValueError:
                    pass
        return None

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = (
            self._rohlik_account.data.get("next_delivery_slot", {})
            .get("data", {})
            .get("preselectedSlots", [])
        )

        # reuse logic from native_value to pick slot_candidate
        preferred_types = ["FIRST", "FIRST_CHEAPEST", "RECOMMENDED"]
        slot_candidate = None
        for ptype in preferred_types:
            for slot in preselected_slots:
                if slot.get("type", "") == ptype:
                    slot_candidate = slot
                    break
            if slot_candidate:
                break
        if slot_candidate is None and len(preselected_slots) > 0:
            slot_candidate = preselected_slots[0]

        if slot_candidate:
            try:
                return {
                    "Delivery Slot End": datetime.strptime(
                        slot_candidate.get("slot", {})
                        .get("interval", {})
                        .get("till", None),
                        "%Y-%m-%dT%H:%M:%S%z",
                    ),
                    "Remaining Capacity Percent": int(
                        slot_candidate.get("slot", {})
                        .get("timeSlotCapacityDTO", {})
                        .get("totalFreeCapacityPercent", 0)
                    ),
                    "Remaining Capacity Message": slot_candidate.get("slot", {})
                    .get("timeSlotCapacityDTO", {})
                    .get("capacityMessage", None),
                    "Price": int(slot_candidate.get("price", 0)),
                    "Title": slot_candidate.get("title", None),
                    "Subtitle": slot_candidate.get("subtitle", None),
                }
            except Exception:  # noqa: E722  (broad but safe for formatting)
                pass
        return None

    @property
    def entity_picture(self) -> str | None:
        # Use generic icon; knuspr uses same CDN path but keep for now.
        return "https://cdn.rohlik.cz/images/icons/preselected-slots/first.png"

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
        preselected_slots = (
            self._rohlik_account.data["next_delivery_slot"]
            .get("data", {})
            .get("preselectedSlots", [])
        )
        state = None
        for slot in preselected_slots:
            if slot.get("type", "") == "ECO":
                state = datetime.strptime(
                    slot.get("slot", {}).get("interval", {}).get("since", None),
                    "%Y-%m-%dT%H:%M:%S%z",
                )
                break
        return state

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns extra state attributes."""
        preselected_slots = (
            self._rohlik_account.data["next_delivery_slot"]
            .get("data", {})
            .get("preselectedSlots", [])
        )
        extra_attrs = None
        for slot in preselected_slots:
            if slot.get("type", "") == "ECO":
                extra_attrs = {
                    "Delivery Slot End": datetime.strptime(
                        slot.get("slot", {}).get("interval", {}).get("till", None),
                        "%Y-%m-%dT%H:%M:%S%z",
                    ),
                    "Remaining Capacity Percent": int(
                        slot.get("slot", {})
                        .get("timeSlotCapacityDTO", {})
                        .get("totalFreeCapacityPercent", 0)
                    ),
                    "Remaining Capacity Message": slot.get("slot", {})
                    .get("timeSlotCapacityDTO", {})
                    .get("capacityMessage", None),
                    "Price": int(slot.get("price", 0)),
                    "Title": slot.get("title", None),
                    "Subtitle": slot.get("subtitle", None),
                }
                break

        return extra_attrs

    @property
    def entity_picture(self) -> str | None:
        return "https://cdn.rohlik.cz/images/icons/preselected-slots/eco.png"

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
        return (
            self._rohlik_account.data.get("delivery", {})
            .get("data", {})
            .get("firstDeliveryText", {})
            .get("default", "Unknown")
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns delivery location."""
        delivery_data = self._rohlik_account.data.get("delivery", {}).get("data", {})
        if delivery_data:
            return {
                "delivery_location": delivery_data.get("deliveryLocationText", ""),
                "delivery_type": delivery_data.get("deliveryType", ""),
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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("id", "N/A")
        )

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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("email", "N/A")
        )

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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("phone", "N/A")
        )

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

    def __init__(self, rohlik_hub: RohlikAccount) -> None:
        super().__init__(rohlik_hub)
        # Dynamically set currency
        self._attr_native_unit_of_measurement = "EUR" if rohlik_hub.is_knuspr else "CZK"

    @property
    def native_value(self) -> float | str:
        """Returns amount of credit as state."""
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("credits", "N/A")
        )

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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
            .get("premiumLimits", {})
            .get("ordersWithoutPriceLimit", {})
            .get("remaining", 0)
        )

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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
            .get("premiumLimits", {})
            .get("freeExpressLimit", {})
            .get("remaining", 0)
        )

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
        return self._rohlik_account.data["bags"].get("current", 0)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns reusable bag details."""
        bags_data = self._rohlik_account.data["bags"]
        extra_attr: dict = {"Max Bags": bags_data.get("max", 0)}
        if bags_data.get("deposit", None):
            extra_attr["Deposit Amount"] = bags_data.get("deposit").get("amount", 0)
            deposit_currency = bags_data.get("deposit").get("currency")
            if not deposit_currency:
                deposit_currency = "EUR" if self._rohlik_account.is_knuspr else "CZK"
            extra_attr["Deposit Currency"] = deposit_currency
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
        return (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
            .get("remainingDays", 0)
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns premium details."""
        premium_data = (
            self._rohlik_account.data.get("login", {})
            .get("data", {})
            .get("user", {})
            .get("premium", {})
        )
        if premium_data:
            return {
                "Premium Type": premium_data.get("premiumMembershipType", ""),
                "Payment Date": premium_data.get("recurrentPaymentDate", ""),
                "Start Date": premium_data.get("startDate", ""),
                "End Date": premium_data.get("endDate", ""),
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

    def __init__(self, rohlik_hub: RohlikAccount) -> None:
        super().__init__(rohlik_hub)
        self._attr_native_unit_of_measurement = "EUR" if rohlik_hub.is_knuspr else "CZK"

    @property
    def native_value(self) -> float:
        """Returns total cart price."""
        return self._rohlik_account.data.get("cart", {}).get("total_price", 0.0)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns cart details."""
        cart_data = self._rohlik_account.data.get("cart", {})
        if cart_data:
            return {
                "Total items": cart_data.get("total_items", 0),
                "Can Order": cart_data.get("can_make_order", False),
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
        if len(self._rohlik_account.data["next_order"]) > 0:
            slot_start = datetime.strptime(
                self._rohlik_account.data["next_order"][0]
                .get("deliverySlot", {})
                .get("since", None),
                "%Y-%m-%dT%H:%M:%S.%f%z",
            )
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
        if len(self._rohlik_account.data["next_order"]) > 0:
            slot_start = datetime.strptime(
                self._rohlik_account.data["next_order"][0]
                .get("deliverySlot", {})
                .get("till", None),
                "%Y-%m-%dT%H:%M:%S.%f%z",
            )
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
        return datetime.strptime(
            self._rohlik_account.data["last_order"][0].get("orderTime", None),
            "%Y-%m-%dT%H:%M:%S.%f%z",
        )

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Returns last order details."""
        last_order_data = self._rohlik_account.data["last_order"][0]
        if len(last_order_data) > 0:
            return {
                "Items": last_order_data.get("itemsCount", None),
                "Price": last_order_data.get("priceComposition", {})
                .get("total", {})
                .get("amount", None),
            }
        return None

    @property
    def icon(self) -> str:
        return ICON_LAST_ORDER

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class ParsedDeliveryTimeSensor(BaseEntity, SensorEntity):
    """Sensor providing parsed delivery time as timestamp."""

    _attr_translation_key = "delivery_eta"
    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        """Return extracted delivery time."""
        delivery_info: list = self._rohlik_account.data["delivery_announcements"][
            "data"
        ]["announcements"]

        if len(delivery_info) == 0:
            return None

        return DeliveryInfo.extract_delivery_datetime(
            delivery_info[0].get("content", ""), self._rohlik_account.is_knuspr
        )

    @property
    def icon(self) -> str:
        return ICON_INFO

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class NextOrderIDSensor(BaseEntity, SensorEntity):
    """Sensor providing next order ID."""

    _attr_translation_key = "next_order_number"
    _attr_should_poll = False

    @property
    def native_value(self) -> str | None:
        """Return ID of the next order if available."""
        if len(self._rohlik_account.data.get("next_order", [])) == 0:
            return None
        return str(self._rohlik_account.data["next_order"][0].get("id"))

    @property
    def icon(self) -> str:
        return ICON_INFO

    async def async_added_to_hass(self) -> None:
        self._rohlik_account.register_callback(self.async_write_ha_state)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)


class UpdateSensor(BaseEntity, SensorEntity):
    """Sensor responsible for fetching data at a dynamic interval."""

    _attr_translation_key = "updated"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = ICON_UPDATE
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_should_poll = False  # We handle our own scheduling

    _LONG_INTERVAL: timedelta = timedelta(minutes=10)
    _SHORT_INTERVAL: timedelta = timedelta(minutes=2)

    def __init__(self, rohlik_account: RohlikAccount) -> None:
        super().__init__(rohlik_account)
        self._attr_native_value = datetime.now(tz=ZoneInfo("Europe/Prague"))
        self._unsub_timer: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        # Register for hub callbacks
        self._rohlik_account.register_callback(self.async_write_ha_state)

        # Schedule the first recurring update
        self._schedule_updates(self._LONG_INTERVAL)

    async def async_will_remove_from_hass(self) -> None:
        self._rohlik_account.remove_callback(self.async_write_ha_state)
        if self._unsub_timer:
            self._unsub_timer()

    def _schedule_updates(self, interval: timedelta) -> None:
        """(Re)schedule periodic updates with the given interval."""
        if self._unsub_timer:
            self._unsub_timer()

        self._unsub_timer = async_track_time_interval(
            self.hass, self._scheduled_update, interval
        )

    async def _scheduled_update(self, _now: datetime) -> None:
        await self.async_update()

    async def async_update(self) -> None:
        """Fetch data from API and dynamically adjust interval."""
        await self._rohlik_account.async_update()
        self._attr_native_value = datetime.now(tz=ZoneInfo("Europe/Prague"))

        # Determine if we need to speed up polling
        now = dt_util.utcnow().astimezone(ZoneInfo("Europe/Prague"))

        # Calculate next delivery start
        next_order_list = self._rohlik_account.data.get("next_order", [])
        within_two_hours = False
        if next_order_list:
            since_str = next_order_list[0].get("deliverySlot", {}).get("since")
            if since_str:
                try:
                    delivery_since = datetime.strptime(
                        since_str, "%Y-%m-%dT%H:%M:%S.%f%z"
                    )
                    if 0 <= (delivery_since - now).total_seconds() <= 7200:
                        within_two_hours = True
                except ValueError:
                    pass

        # Adjust interval based on time to delivery
        desired_interval = (
            self._SHORT_INTERVAL if within_two_hours else self._LONG_INTERVAL
        )

        # Check current interval (approximate by comparing callback frequency)
        # We will simply reschedule when desired differs from long vs short flag
        current_short = (
            self._unsub_timer is not None and desired_interval == self._SHORT_INTERVAL
        )
        if within_two_hours != current_short:
            self._schedule_updates(desired_interval)
