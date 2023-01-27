from typing import Any

import requests


class SimpleAwsError(Exception):
    """Base simple_aws exception"""


class InvalidParam(SimpleAwsError):
    def __init__(self, name: str, val: Any, message: str) -> None:
        super().__init__(name, val, message)
        self.name = name
        self.val = val
        self.message = message


class RequestFailed(SimpleAwsError):
    def __init__(self, response: requests.Response) -> None:
        super().__init__(response.status_code, response.url)
        self.response = response


class UnexpectedResponse(SimpleAwsError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class NotFound(SimpleAwsError):
    def __init__(self, object_name: str, service_name: str) -> None:
        super().__init__(object_name, service_name)
