import hashlib
import hmac
from base64 import b64encode
from binascii import hexlify
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timezone
from functools import reduce
from typing import Mapping
from typing import Optional
from typing import Union
from urllib.parse import quote

from furl.furl import furl

from simple_aws.typedef import METHODS

from .credentials import Credentials

CONTENT_TYPE = "application/x-www-form-urlencoded"
AWS_ALGORITHM = "AWS4-HMAC-SHA256"
AWS_REQUEST = "aws4_request"


@dataclass(frozen=True)
class AwsAuthV4:
    credentials: Credentials
    service: str
    use_default_headers: bool = True

    def headers(
        self,
        method: METHODS,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        data: Optional[bytes] = None,
        content_type: Optional[str] = None,
        now: Optional[datetime] = None,
    ):
        now = now or datetime.now(timezone.utc)
        data = data or b""
        content_type = content_type or CONTENT_TYPE
        f_url = furl(url)
        payload_hash = self.hash_payload(data)
        headers = self._base_headers(
            f_url, headers or {}, data, content_type, now
        )

        signed_headers, signature = self.make_signature(
            method, f_url, payload_hash, now, headers
        )
        credential = self.make_credential(now)
        authorization_header = (
            f"{AWS_ALGORITHM} Credential={credential},"
            f"SignedHeaders={signed_headers},"
            f"Signature={signature}"
        )
        return headers | {
            "authorization": authorization_header,
            "x-amz-content-sha256": payload_hash,
        }

    def hash_payload(self, payload: Optional[bytes] = None):
        return hashlib.sha256(payload or b"").hexdigest()

    def make_signature(
        self,
        method: METHODS,
        url: Union[str, furl],
        payload_hash: str,
        now: datetime,
        headers: Optional[Mapping[str, str]] = None,
    ) -> tuple[str, str]:
        f_url = furl(url) if isinstance(url, str) else url.copy()
        now = now
        headers = headers or {}
        signed_headers, canonical_request = self._get_canonical_request(
            method, f_url, headers, payload_hash
        )
        signed_string = self._create_sign_string(
            now, hashlib.sha256(canonical_request.encode()).hexdigest()
        )
        return signed_headers, self.aws4_sign_string(signed_string, now)

    def _base_headers(
        self,
        url: furl,
        headers: Mapping[str, str],
        data: bytes,
        content_type: str,
        now: datetime,
    ):
        base_headers = {
            "host": url.host,
            "x-amz-date": amz_dateformat(now),
        }
        if self.use_default_headers:
            base_headers |= {
                "content-md5": b64encode(hashlib.md5(data).digest()).decode(),
                "content-type": content_type,
            }
        result = base_headers | headers
        return {key: result[key] for key in sorted(result)}

    def _get_canonical_request(
        self,
        method: METHODS,
        url: furl,
        headers: Mapping[str, str],
        payload_hash: str,
    ) -> tuple[str, str]:
        header_keys = sorted(headers)
        signed_headers = ";".join(header_keys)
        return signed_headers, "\n".join(
            (
                method,
                quote(str(url.path) or "/"),
                "&".join(
                    "=".join((quote(key), quote(value or "", safe="")))
                    for key, value in url.query.params.iteritems()
                ),
                "\n".join(
                    ":".join((str.lower(key), str.strip(headers[key])))
                    for key in header_keys
                )
                + "\n",
                signed_headers,
                payload_hash,
            )
        )

    def _create_sign_string(self, now: datetime, hashed_canonical: str) -> str:
        return "\n".join(
            (
                AWS_ALGORITHM,
                amz_dateformat(now),
                self._credential_scope(now),
                hashed_canonical,
            )
        )

    def aws4_sign_string(self, string_to_sign: str, now: datetime) -> str:
        key_parts = (
            b"AWS4" + self.credentials.secret_access_key.encode(),
            _make_aws_date(now),
            self.credentials.region,
            self.service,
            AWS_REQUEST,
            string_to_sign,
        )
        signature_bytes: bytes = reduce(
            _aws4_reduce_signature, key_parts  # type: ignore
        )
        return hexlify(signature_bytes).decode()

    def _credential_scope(self, now: date):
        return "/".join(
            (
                _make_aws_date(now),
                self.credentials.region,
                self.service,
                AWS_REQUEST,
            )
        )

    def _initialize_header_signature(self, dt: date):
        return " ".join(
            (
                AWS_ALGORITHM,
                f"Credential={self.make_credential( dt)}",
            )
        )

    def make_credential(self, now: date):
        return "/".join(
            (self.credentials.access_key_id, self._credential_scope(now))
        )


def _aws4_reduce_signature(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _make_aws_date(now: date):
    return "".join(
        # make sure to use date, because datetime is a date child
        (date(now.year, now.month, now.day))
        .isoformat()
        .split("-")
    )


def amz_dateformat(dt: datetime):
    return dt.strftime("%Y%m%dT%H%M%SZ")
