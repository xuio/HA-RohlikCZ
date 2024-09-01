import logging
import requests

from .const import LOGIN_URL, DELIVERY_URL, NEXT_ORDER_URL

_LOGGER = logging.getLogger(__name__)


class RohlikCZAPI:

    def __init__(self, username, password):
        self._user = username
        self._pass = password
        self._session = requests.session()

    def login(self):
        res = self._session.post(url=LOGIN_URL, json={"email": self._user, "password": self._pass, "name": ""})
        if res.status_code != 200:
            raise ValueError("Login failed")
        return res

    def get_nearest_delivery(self):
        res = self._session.get(DELIVERY_URL)
        res_as_dict = res.json()
        if res_as_dict["status"] == 200:
            return res_as_dict["data"]
        else:
            raise ValueError("No response from API")

    def get_next_order(self):
        res = self._session.get(NEXT_ORDER_URL)
        res_as_dict = res.json()
        if res_as_dict["status"] == 200:
            return res_as_dict["data"]
        else:
            raise ValueError("No response from API")