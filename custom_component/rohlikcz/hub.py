from __future__ import annotations
from collections.abc import Callable
from typing import Any, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .rohlik_api import RohlikCZAPI


class RohlikAccount:
    """Setting RohlikCZ account as device."""

    def __init__(self, hass: HomeAssistant, username: str, password: str) -> None:
        """Initialize account info."""
        super().__init__()
        self._hass = hass
        self._username: str = username
        self._password: str = password
        self.user_data: dict[str, Any] = {}
        self.next_order_data: dict = {}
        self._callbacks: set[Callable[[], None]] = set()

    @property
    def user_id(self) -> str:
        """ID for user account."""
        return self.user_data["data"]["user"]["id"]

    @property
    def device_info(self) -> DeviceInfo:
        """ Provides a device info. """
        return {"identifiers": {(DOMAIN, self.user_id)}, "name": self.name, "manufacturer": "Rohlík CZ"}

    @property
    def name(self) -> str:
        """Provides name for account."""
        return self.user_data["data"]["user"]["name"]

    @property
    def is_premium(self) -> str:
        """ Provides whether the account is premium."""
        return self.user_data["data"]["user"]["premium"]["active"]

    @property
    def is_parent(self) -> str:
        """ Provides if the account is in Rohlíček klub."""
        return self.user_data["data"]["user"]["parentsClub"]

    @property
    def is_ordered(self) -> str:
        """ Provides if the account is in Rohlíček klub."""
        return self.user_data["data"]["user"]["parentsClub"]

    @property
    def credit_amount(self) -> int:
        """ Provides remaining credit amount."""
        return self.user_data["data"]["user"]["credits"]

    @property
    def nearest_delivery(self):
        """Return a text of nearest delivery time."""
        pass

    async def async_update(self) -> None:
        """ Updates the data from API."""
        rohlik_session = RohlikCZAPI(self._username, self._password)
        self.user_data = await rohlik_session.login()
        self.next_order_data = await rohlik_session.get_next_order()
        await self.publish_updates()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when there are new data."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    async def publish_updates(self) -> None:
        """Schedule call to all registered callbacks."""
        for callback in self._callbacks:
            callback()


