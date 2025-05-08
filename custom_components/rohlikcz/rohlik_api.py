"""
RohlikCZ API Client

This module provides an asynchronous API client for interacting with Rohlik.cz, a Czech online grocery delivery service. It allows logging in, retrieving account data, searching products, managing shopping carts, and accessing shopping lists.

Example:
    from rohlik_api import RohlikCZAPI

    async def example():
        client = RohlikCZAPI('username@example.com', 'password')
        data = await client.get_data()
        print(data)
"""

import logging
import requests
from requests import Response
from requests.exceptions import RequestException
from typing import TypedDict
from .errors import InvalidCredentialsError, RohlikczError, AddressNotSetError
import asyncio
import functools

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.rohlik.cz"

class Product(TypedDict):
    """
    TypedDict representing a Rohlik product to be added to cart.

    Attributes:
        product_id (int): The unique identifier of the product
        quantity (int): The quantity of the product to add
    """
    product_id: int
    quantity: int


class RohlikCZAPI:
    """
    API client for interacting with Rohlik.cz services.

    This class provides methods to authenticate with Rohlik.cz and perform
    various operations such as retrieving account data, searching for products,
    adding products to cart, and accessing shopping lists.

    Attributes:
        endpoints (dict): Dictionary of available API endpoints

    """
    def __init__(self, username, password):
        """
        Initialize the Rohlik API client.

        Args:
            username (str): Email address used for Rohlik.cz login
            password (str): Password for Rohlik.cz account
        """
        self._user = username
        self._pass = password
        self._user_id = None
        self._address_id = None
        self.endpoints = {}

    def _run_in_executor(self, func, *args, **kwargs):
        """
        Run blocking requests calls in a thread executor to maintain async compatibility.

        This helper method ensures that blocking HTTP calls don't block the asyncio event loop
        by running them in a separate thread executor.

        Args:
            func (callable): The function to execute (typically a requests method)
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            asyncio.Future: A future representing the execution of the function
        """
        return asyncio.get_event_loop().run_in_executor(
            None, functools.partial(func, *args, **kwargs)
        )

    async def login(self, session):
        """
        Authenticate with the Rohlik.cz service.

        Args:
            session (requests.Session): An active requests session to use for authentication

        Returns:
            dict: The JSON response containing authentication data and user information

        Raises:
            requests.exceptions.RequestException: If the login request fails
        """

        login_data = {"email": self._user, "password": self._pass, "name": ""}
        login_url = f"{BASE_URL}/services/frontend-service/login"

        try:
            login_response: Response = await self._run_in_executor(
                session.post,
                login_url,
                json=login_data
            )

            login_response: dict = login_response.json()

            if login_response["status"] != 200:
                if login_response["status"] == 401:
                    raise InvalidCredentialsError(login_response["messages"][0]["content"])
                else:
                    raise RohlikczError(f"Unknown error occurred during login: {login_response["messages"][0]["content"]}")

            if not self._user_id:
                self._user_id = login_response.get("data", {}).get("user", {}).get("id", None)

            if not self._address_id:
                try:
                    self._address_id = login_response.get("data", {}).get("address", {}).get("id", None)
                except AttributeError as err:
                    raise AddressNotSetError(f"Address is not set in the account: {err}")

            return login_response

        except RequestException:
            _LOGGER.error("Cannot connect to website! Check your internet connection and try again")


    async def get_data(self):
        """
        Retrieve all account data from Rohlik.cz in a single operation.

        Returns:
            dict: A dictionary containing all data from various Rohlik endpoints,
                 including login information, delivery details, cart contents,
        """
        session = requests.Session()
        result: dict = {}
        self.endpoints = {
            "delivery": "/services/frontend-service/first-delivery?reasonableDeliveryTime=true",
            "next_order": "/api/v3/orders/upcoming",
            "announcements": "/services/frontend-service/announcements/top",
            "cart": "/services/frontend-service/v2/cart",
            "bags": "/api/v1/reusable-bags/user-info",
            "timeslot": "/services/frontend-service/v1/timeslot-reservation",
            "last_order": "/api/v3/orders/delivered?offset=0&limit=1",
            "premium_profile": "/services/frontend-service/premium/profile",
            "next_delivery_slot": "/services/frontend-service/timeslots-api/",
            "delivery_announcements": "/services/frontend-service/announcements/delivery"
        }

        result["login"] = await self.login(session)

        try:
            # Step 2: Get data from all other endpoints
            for endpoint, path in self.endpoints.items():

                if endpoint == "next_delivery_slot":
                    path = self.endpoints["next_delivery_slot"] + f"0?userId={self._user_id}&addressId={self._address_id}&reasonableDeliveryTime=true"

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

    async def add_to_cart(self, product_list: list[Product]):
        """
        Add multiple products to the shopping cart.

        Args:
            product_list (list[Product]): A list of Product objects containing product_id and quantity for each product to be added to the cart
        Returns:
            list: A list of product IDs that were successfully added to the cart
        """

        session = requests.Session()
        await self.login(session)

        try:
            search_url = "/services/frontend-service/v2/cart"
            added_products = []

            for product in product_list:
                search_payload = {
                    "actionId": None,
                    "productId": int(product["product_id"]),
                    "quantity": int(product["quantity"]),
                    "recipeId": None,
                    "source": "true:Shopping Lists"
                }
                try:
                    search_response = await self._run_in_executor(
                        session.post,
                        f"{BASE_URL}{search_url}",
                        json=search_payload
                    )
                    search_response.raise_for_status()
                    added_products.append(product["product_id"])
                except RequestException as err:
                    _LOGGER.error(f"Error adding {product["product_id"]} due to {err}")

            return added_products

        except RequestException as err:
            _LOGGER.error(f"Request failed: {err}")
            raise ValueError("Request failed")
        finally:
            await self._run_in_executor(session.close)

    async def search_product(self, product_name):
        """
        Search for products by name and return the first matching product.

        Args:
            product_name (str): The name or search term for the product

        Returns:
            dict: The first matching product's details, or None if no products found
        """

        session = requests.Session()

        try:
            search_url = "/services/frontend-service/search-metadata"

            search_payload = {
                "search": product_name,
                "offset": 0,
                "limit": 1,
                "companyId" : 1,
                "filterData": {"filters": []},
                "canCorrect": True
            }
            await self.login(session)
            search_response = await self._run_in_executor(
                session.get,
                f"{BASE_URL}{search_url}",
                params=search_payload
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            if len(search_data["data"]["productList"]) > 0:
                return search_data["data"]["productList"][0]
            else:
                return None

        except RequestException as err:
            _LOGGER.error(f"Request failed: {err}")
            raise ValueError("Request failed")
        finally:
            await self._run_in_executor(session.close)

    async def get_shopping_list(self, shopping_list_id=None):
        """
        Retrieve a shopping list by its ID.

        Args:
            shopping_list_id (str, optional): The ID of the shopping list to retrieve. Must be provided.

        Returns:
            dict: The shopping list details
        """

        session = requests.Session()

        try:
            if not shopping_list_id:
                raise ValueError("Missing argument - shopping list id")

            shopping_list_url = f"/api/v1/shopping-lists/id/{shopping_list_id}"

            await self.login(session)
            search_response = await self._run_in_executor(
                session.get,
                f"{BASE_URL}{shopping_list_url}",
            )
            search_response.raise_for_status()
            search_data = search_response.json()
            return search_data

        except RequestException as err:
            _LOGGER.error(f"Request failed: {err}")
            raise ValueError("Request failed")
        finally:
            await self._run_in_executor(session.close)
