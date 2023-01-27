from dataclasses import dataclass

import requests
from gyver.context import Adapter


@dataclass(frozen=True)
class HttpProvider(Adapter[requests.Session]):
    verify_ssl: bool = True

    def is_closed(self, client: requests.Session) -> bool:
        """`requests.Session` doesn't have a closed state
        so we implement this only for interface purposes"""
        del client
        return False

    def release(self, client: requests.Session) -> None:
        client.close()

    def new(self):
        return self._setup_request()

    def _setup_request(self) -> requests.Session:
        session = requests.Session()
        session.verify = self.verify_ssl
        return session
