import logging
import requests
from requests.exceptions import RequestException
import asyncio
import functools

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.rohlik.cz"


class RohlikCZAPI:
    def __init__(self, username, password):
        self._user = username
        self._pass = password
        self._user_id = None
        self._address_id = None
        self.endpoints = {
            "login": "/services/frontend-service/login",
            "delivery": "/services/frontend-service/first-delivery?reasonableDeliveryTime=true",
            "next_order": "/api/v3/orders/upcoming",
            "announcements": "/services/frontend-service/announcements/top",
            "cart": "/services/frontend-service/v2/cart",
            "bags": "/api/v1/reusable-bags/user-info",
            "timeslot": "/services/frontend-service/v1/timeslot-reservation",
            "last_order": "/api/v3/orders/delivered?offset=0&limit=1",
            "premium_profile": "/services/frontend-service/premium/profile",
            "next_delivery_slot": f"/services/frontend-service/timeslots-api/"
        }

    def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking requests calls in a thread executor to maintain async compatibility"""
        return asyncio.get_event_loop().run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )

    async def get_data(self):
        """
        One-step method that:
        1. Creates a new session
        2. Logs in
        3. Gets data from all endpoints
        4. Closes the session
        5. Returns all data including login response
        """
        session = requests.Session()
        result = {}

        try:
            # Step 1: Login
            login_data = {"email": self._user, "password": self._pass, "name": ""}
            login_url = f"{BASE_URL}{self.endpoints['login']}"

            login_response = await self._run_in_executor(
                session.post,
                login_url,
                json=login_data
            )
            login_response.raise_for_status()
            result["login"] = login_response.json()
            self._user_id = result["login"].get("data", {}).get("user", {}).get("id", None)
            self._address_id = result["login"].get("data", {}).get("address", {}).get("id", None)


            # Step 2: Get data from all other endpoints
            for endpoint, path in self.endpoints.items():
                if endpoint == "login":
                    continue  # Already handled

                if endpoint == "next_delivery_slot":
                    self.endpoints["next_delivery_slot"] = self.endpoints["next_delivery_slot"] + f"0?userId={self._user_id}&addressId={self._address_id}&reasonableDeliveryTime=true"

                try:
                    url = f"{BASE_URL}{path}"
                    response = await self._run_in_executor(session.get, url)
                    response.raise_for_status()
                    result[endpoint] = response.json()
                except RequestException as err:
                    _LOGGER.error(f"Error fetching {endpoint}: {err}")
                    result[endpoint] = None

            return result

        except RequestException as err:
            _LOGGER.error(f"Login failed: {err}")
            raise ValueError("Login failed")
        finally:
            # Step 3: Close the session
            await self._run_in_executor(session.close)
