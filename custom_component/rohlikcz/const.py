"""
Defining constants for the project.
"""
from aiohttp import ClientTimeout
from typing import Final


LOGIN_URL = "https://www.rohlik.cz/services/frontend-service/login"
DELIVERY_URL = "https://www.rohlik.cz/services/frontend-service/first-delivery?reasonableDeliveryTime=true"
NEXT_ORDER_URL = ""

HTTP_TIMEOUT: Final = ClientTimeout(total=10)
DOMAIN = "rohlikcz"

"""Icons"""
ICON_PREMIUM = "mdi:cart-plus"
ICON_PARENTCLUB = "mdi:human-male-female-child"
ICON_CREDIT = "mdi:cash-multiple"
