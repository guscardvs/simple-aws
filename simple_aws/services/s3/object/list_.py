import re
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET

from gyver.url import URL

from simple_aws.exc import InvalidParam
from simple_aws.exc import RequestFailed
from simple_aws.exc import UnexpectedResponse
from simple_aws.services.s3.models import FileInfo
from simple_aws.utils import xmlns

from .core import S3Core

MAX_CHUNKSIZE = 1000

xmlns_re = re.compile(f' xmlns="{re.escape(xmlns)}"'.encode())


@dataclass(frozen=True)
class List:
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
        return self.core.get_uri_copy().add(
            {"list-type": "2", "max-keys": str(self.chunksize)}, path="/"
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
                url = self._prepare_url(base_url, continuation_token)
                response = client.get(
                    url,
                )
                if not response.ok:
                    print(response.text)
                    raise RequestFailed(response)
                xml_content = ET.fromstring(
                    xmlns_re.sub(b"", response.content)
                )
                for contents in xml_content.findall("Contents"):
                    yield FileInfo.parse_obj(
                        {items.tag: items.text for items in contents}
                    )
                if self._list_is_exhausted(xml_content):
                    break
                if (
                    t := xml_content.find("NextContinuationToken")
                ) is not None:
                    continuation_token = t.text
                else:
                    raise UnexpectedResponse("unexpected response from S3")

    def _list_is_exhausted(self, xml_content: ET.Element):
        return (
            t := xml_content.find("IsTruncated")
        ) is not None and t.text == "false"

    def _prepare_url(
        self,
        base_url: URL,
        continuation_token: Optional[str],
    ):
        url = base_url.copy()
        if self.prefix:
            prefix = self.prefix.removeprefix("/")
            url.add({"prefix": prefix})
        if continuation_token:
            url.add({"continuation-token": continuation_token})
        return url
