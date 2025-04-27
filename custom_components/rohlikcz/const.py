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
ICON_REUSABLE = "mdi:recycle"
ICON_UPDATE = "mdi:update"
ICON_NO_LIMIT = "mdi:cash-100"
ICON_FREE_EXPRESS = "mdi:truck-snowflake"
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
ICON_LAST_ORDER = "mdi:calendar-range"
ICON_NEXT_ORDER_SINCE = "mdi:clock-start"
ICON_NEXT_ORDER_TILL = "mdi:clock-end"
ICON_CALENDAR_CHECK = "mdi:calendar-check"
ICON_CALENDAR_REMOVE = "mdi:calendar-remove"
ICON_INFO = "mdi:information-outline"
