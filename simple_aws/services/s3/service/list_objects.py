import re
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree

from furl.furl import furl

from simple_aws.exc import InvalidParam
from simple_aws.exc import RequestFailed
from simple_aws.exc import UnexpectedResponse
from simple_aws.services.s3.models import FileInfo

from .handle_object import S3Core

MAX_CHUNKSIZE = 1000

xmlns = "http://s3.amazonaws.com/doc/2006-03-01/"
xmlns_re = re.compile(f' xmlns="{re.escape(xmlns)}"'.encode())


@dataclass(frozen=True)
class ListObjects:
    core: S3Core
    prefix: Optional[str] = None
    chunksize: int = MAX_CHUNKSIZE

    def __post_init__(self):
        if not (1 <= self.chunksize <= MAX_CHUNKSIZE):
            raise InvalidParam(
                "chunksize",
                self.chunksize,
                "Chunksize must be greater "
                f"than 1 and lesser than {MAX_CHUNKSIZE}",
            )

    def new_url(self):
        return self.core.base_uri.copy().add(
            {"list-type": 2, "max-keys": self.chunksize}
        )

    @property
    def context(self):
        return self.core.context

    @property
    def aws_auth(self):
        return self.core.aws_auth

    def __iter__(self):
        yield from self.iter()

    def iter(self):
        base_url = self.new_url()
        continuation_token = None
        with self.context.begin() as client:
            while True:
                str_url = self._prepare_url(base_url, continuation_token)
                response = client.get(
                    str_url,
                    headers=self.aws_auth.headers(
                        "GET",
                        str_url,
                    ),
                )
                if not response.ok:
                    raise RequestFailed(response)
                xml_content = ElementTree.fromstring(
                    xmlns_re.sub(b"", response.content)
                )
                for contents in xml_content.findall("Contents"):
                    yield FileInfo.parse_obj(
                        {items.tag: items.text for items in contents}
                    )
                if (
                    t := xml_content.find("IsTruncated")
                ) is not None and t.text == "false":
                    break
                if (
                    t := xml_content.find("NextContinuationToken")
                ) is not None:
                    continuation_token = t.text
                else:
                    raise UnexpectedResponse("unexpected response from S3")

    def _prepare_url(
        self,
        base_url: furl,
        continuation_token: Optional[str],
    ):
        url = base_url.copy()
        if self.prefix:
            prefix = self.prefix.removeprefix("/")
            url.add({"prefix": prefix})
        if continuation_token:
            url.add({"continuation-token": continuation_token})
        return str(url)
