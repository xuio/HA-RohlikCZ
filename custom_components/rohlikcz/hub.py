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
        self._rohlik_api = RohlikCZAPI(self._username, self._password)
        self.data: dict = {}
        self._callbacks: set[Callable[[], None]] = set()


    @property
    def device_info(self) -> DeviceInfo:
        """ Provides a device info. """
        return {"identifiers": {(DOMAIN, self.data["login"]["data"]["user"]["id"])}, "name": self.data["login"]["data"]["user"]["name"], "manufacturer": "Rohlík.cz"}

    @property
    def name(self) -> str:
        """Provides name for account."""
        return self.data["login"]["data"]["user"]["name"]

    async def async_update(self) -> None:
        """ Updates the data from API."""

        self.data = await self._rohlik_api.get_data()

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


