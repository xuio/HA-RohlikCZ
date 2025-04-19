"""
Defining constants for the project.
"""
from aiohttp import ClientTimeout
from typing import Final


HTTP_TIMEOUT: Final = ClientTimeout(total=10)
DOMAIN = "rohlikcz"

"""Icons"""
ICON_PARENTCLUB = "mdi:human-male-female-child"
ICON_CREDIT = "mdi:cash-multiple"
ICON_REUSABLE = "mdi:"
ICON_UPDATE = "mdi:"
ICON_NO_LIMIT = "mdi:"
ICON_FREE_EXPRESS = "mdi:"
ICON_PREMIUM = "mdi:medal"
ICON_ORDER = "mdi:package-variant-closed"
ICON_TIMESLOT = "mdi:calendar-clock"
ICON_DELIVERY = "mdi:truck-delivery"
ICON_BAGS = "mdi:shopping"
ICON_CART = "mdi:cart"
ICON_ACCOUNT = "mdi:account"
ICON_EMAIL = "mdi:email"
ICON_PHONE = "mdi:phone"
ICON_PREMIUM_DAYS = "mdi:calendar-clock"
