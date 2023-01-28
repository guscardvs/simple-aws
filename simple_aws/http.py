from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import Mapping
from typing import Optional
from typing import Union
from typing import overload

import requests
from gyver.context import Adapter
from gyver.url import URL
from gyver.utils import lazyfield

from simple_aws.auth import AwsAuthV4
from simple_aws.exc import InvalidParam

from .credentials import Credentials


@dataclass(frozen=True)
class AuthHttpClient:
    credentials: Credentials
    service: str
    use_default_headers: bool = True
    verify_ssl: bool = True

    @lazyfield
    def aws_auth(self):
        return AwsAuthV4(
            self.credentials, self.service, self.use_default_headers
        )

    @lazyfield
    def session(self):
        session = requests.Session()
        session.verify = self.verify_ssl
        return session

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.session.close()

    def head(
        self,
        url: URL,
        headers: Optional[Mapping[str, str]] = None,
        raw: bool = False,
    ):
        headers = headers or {}
        headers = (
            headers
            if raw
            else self.aws_auth.headers("HEAD", url, headers=headers)
        )
        return self.session.head(url.encode(), headers=headers)

    def get(
        self,
        url: URL,
        headers: Optional[Mapping[str, str]] = None,
        raw: bool = False,
    ):
        headers = headers or {}
        headers = (
            headers
            if raw
            else self.aws_auth.headers("GET", url, headers=headers)
        )
        return self.session.get(url.encode(), headers=headers)

    @overload
    def post(
        self,
        url: URL,
        data: bytes = b"",
        headers: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, bytes]] = None,
        raw: bool = False,
    ) -> requests.Response:
        ...

    @overload
    def post(
        self,
        url: URL,
        data: Mapping[str, Any],
        headers: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, bytes]] = None,
        *,
        raw: Literal[True],
    ) -> requests.Response:
        ...

    def post(
        self,
        url: URL,
        data: Union[bytes, Mapping[str, Any]] = b"",
        headers: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, bytes]] = None,
        raw: bool = False,
    ):
        headers = headers or {}
        if not raw:
            if not isinstance(data, bytes):
                raise InvalidParam(
                    "data", data, "Requests using data as mapping must be raw"
                )
            headers = self.aws_auth.headers(
                "POST", url, headers=headers, data=data
            )
        return self.session.post(
            url.encode(), data=data, headers=headers, files=files
        )

    def put(
        self,
        url: URL,
        data: Union[bytes, Mapping[str, Any]] = b"",
        headers: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, bytes]] = None,
        raw: bool = False,
    ):
        headers = headers or {}
        if not raw:
            if not isinstance(data, bytes):
                raise InvalidParam(
                    "data", data, "Requests using data as mapping must be raw"
                )
            headers = self.aws_auth.headers(
                "PUT", url, headers=headers, data=data
            )
        return self.session.put(
            url.encode(), data=data, headers=headers, files=files
        )


@dataclass(frozen=True)
class AuthHttpAdapter(Adapter[AuthHttpClient]):
    credentials: Credentials
    service: str
    use_default_headers: bool = True
    verify_ssl: bool = True

    def is_closed(self, client: AuthHttpClient) -> bool:
        """`requests.Session` doesn't have a closed state
        so we implement this only for interface purposes"""
        del client
        return False

    def release(self, client: AuthHttpClient) -> None:
        client.close()

    def new(self):
        return AuthHttpClient(
            self.credentials,
            self.service,
            self.use_default_headers,
            self.verify_ssl,
        )
