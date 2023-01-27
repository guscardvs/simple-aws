from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from http import HTTPStatus
from typing import Optional

from furl.furl import furl

from simple_aws.auth import AWS_ALGORITHM
from simple_aws.auth import amz_dateformat
from simple_aws.exc import InvalidParam, NotFound
from simple_aws.exc import RequestFailed
from simple_aws.services.s3.models import FileInfo, StorageClass
from simple_aws.typedef import METHODS

from .handle_object import S3Core

DAY = 86400
WEEK = 604800


@dataclass(frozen=True)
class HandleObject:
    core: S3Core
    object_name: str
    version: Optional[str] = None

    @property
    def aws_auth(self):
        return self.core.aws_auth

    def new_url(self):
        return self.core.base_uri.copy().add(path=self.object_name)

    def download(self):
        url = self.presigned_url(expires=30)
        with self.core.context.begin() as client:
            response = client.get(url)
            if not response.ok:
                raise RequestFailed(response)
            return response.content

    def presigned_url(self, expires: int = DAY):
        url = self._append_get_object_params("GET", expires)
        if self.version:
            url.add({"v": self.version})
        return str(url)

    def info(self):
        url = str(self.new_url())
        with self.core.context.begin() as client:
            response = client.head(
                url, headers=self.aws_auth.headers("HEAD", url)
            )
            if not response.ok:
                if response.status_code == HTTPStatus.NOT_FOUND:
                    raise NotFound(self.object_name, "s3")
                raise RequestFailed(response)
            # formatting last_modifies from this format:
            # Fri, 27 Jan 2023 10:21:12 GMT
            return FileInfo.parse_obj(
                {
                    "key": self.object_name,
                    "last_modified": datetime.strptime(
                        response.headers["Last-Modified"],
                        "%a, %d %b %Y %H:%M:%S GMT",
                    ),
                    "size": response.headers["Content-Length"],
                    "e_tag": response.headers["ETag"].strip("\"'"),
                    "storage_class": response.headers.get(
                        "x-amz-storage-class", "UNKNOWN"
                    ),
                }
            )

    def _append_get_object_params(
        self,
        method: METHODS,
        expires: int,
    ) -> furl:
        if not 1 <= expires <= WEEK:
            raise InvalidParam(
                "expires",
                expires,
                f"Expires must be greater than 1 and lower than a {WEEK=}",
            )
        timestamp = datetime.now(timezone.utc)
        url = self.new_url()
        url.add(
            {
                "X-Amz-Algorithm": AWS_ALGORITHM,
                "X-Amz-Credential": self.aws_auth.make_credential(timestamp),
                "X-Amz-Date": amz_dateformat(timestamp),
                "X-Amz-Expires": str(expires),
                "X-Amz-SignedHeaders": "host",
            }
        )
        _, signature = self.aws_auth.make_signature(
            method,
            str(url),
            "UNSIGNED-PAYLOAD",
            timestamp,
            {"host": str(url.host)},
        )
        url.add({"X-Amz-Signature": signature})
        return url
