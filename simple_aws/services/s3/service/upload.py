import base64
import mimetypes
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from http import HTTPStatus
from typing import Optional
from typing import cast

from gyver.utils import json
from gyver.utils import lazyfield

from simple_aws.auth import AWS_ALGORITHM
from simple_aws.auth import amz_dateformat
from simple_aws.exc import RequestFailed
from simple_aws.services.s3.models import UploadParams

from .handle_object import S3Core

DEFAULT_MIMETYPE = "application/octet-stream"


@dataclass(frozen=True)
class Upload:
    core: S3Core
    object_name: str
    content: bytes
    content_type: Optional[str] = None

    @lazyfield
    def mimetype(self):
        return (
            self.content_type
            or mimetypes.guess_type(self.object_name.strip("/"))[0]
            or DEFAULT_MIMETYPE
        )

    @lazyfield
    def content_size(self):
        return len(self.content)

    @property
    def config(self):
        return self.core.config

    @property
    def aws_auth(self):
        return self.core.aws_auth

    def upload(self):
        parts = self.fileparts()
        fields = self._put_object_fields(
            parts[0] if len(parts) > 1 else "",
            parts[-1],
            expires=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        with self.core.context.begin() as client:
            response = client.post(
                str(self.core.base_uri), fields, files={"file": self.content}
            )
            if response.status_code != HTTPStatus.NO_CONTENT:
                raise RequestFailed(response)

    def fileparts(self):
        object_name = self.object_name.strip("/")
        return object_name.rsplit("/", 1)

    def _put_object_fields(
        self,
        path: str,
        filename: str,
        content_disp: bool = True,
        expires: Optional[datetime] = None,
    ) -> UploadParams:
        key = "/".join(item.strip("/") for item in (path, filename))
        policy_conditions = [
            {"bucket": self.config.bucket_name},
            {"key": key},
            {"content-type": self.mimetype},
            ["content-length-range", self.content_size, self.content_size],
        ]
        content_disposition_fields = {}
        if content_disp:
            policy_conditions.append(
                content_disposition_fields := {
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        timestamp = datetime.now(timezone.utc)
        policy_conditions.extend(self._upload_additional_conditions(timestamp))

        expiration = expires or timestamp + timedelta(seconds=60)
        policy = {
            "expiration": f"{expiration:%Y-%m-%dT%H:%M:%SZ}",
            "conditions": policy_conditions,
        }
        b64_policy = base64.b64encode(json.dumps(policy).encode()).decode()
        return cast(
            UploadParams,
            {
                "Key": key,
                "Content-Type": self.mimetype,
                **content_disposition_fields,
                "Policy": b64_policy,
                **self._signed_upload_fields(timestamp, b64_policy),
            },
        )

    def _upload_additional_conditions(self, timestamp: datetime):
        return [
            {"X-Amz-Credential": self.aws_auth.make_credential(timestamp)},
            {"X-Amz-Algorithm": AWS_ALGORITHM},
            {"X-Amz-Date": amz_dateformat(timestamp)},
        ]

    def _signed_upload_fields(self, timestamp: datetime, policy: str):
        return {
            "X-Amz-Algorithm": AWS_ALGORITHM,
            "X-Amz-Credential": self.aws_auth.make_credential(timestamp),
            "X-Amz-Date": amz_dateformat(timestamp),
            "X-Amz-Signature": self.aws_auth.aws4_sign_string(
                policy, timestamp
            ),
        }
