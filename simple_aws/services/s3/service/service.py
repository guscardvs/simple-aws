from dataclasses import dataclass
from dataclasses import field
from typing import Optional

from gyver.utils import lazyfield

from simple_aws.config import make_default_factory
from simple_aws.credentials import Credentials
from simple_aws.http import HttpProvider
from simple_aws.services.s3.config import S3Config

from .handle_object import S3Core
from .get import DAY
from .get import HandleObject
from .list_objects import MAX_CHUNKSIZE
from .list_objects import ListObjects
from .upload import Upload


@dataclass(frozen=True)
class S3Service:
    credentials: Credentials
    config: S3Config = field(default_factory=make_default_factory(S3Config))
    http_provider: HttpProvider = field(default_factory=HttpProvider)

    @lazyfield
    def core(self):
        return S3Core(self.credentials, self.config, self.http_provider)

    def upload(
        self,
        object_name: str,
        content: bytes,
        *,
        content_type: Optional[str] = None
    ) -> None:
        return Upload(self.core, object_name, content, content_type).upload()

    def list_objects(
        self,
        prefix: Optional[str] = None,
        chunksize: int = MAX_CHUNKSIZE,
    ):
        return ListObjects(self.core, prefix, chunksize)

    def download(
        self,
        object_name: str,
        version: Optional[str] = None,
    ) -> bytes:
        return self._make_get_object(object_name, version).download()

    def create_presigned_get(
        self,
        object_name: str,
        version: Optional[str] = None,
        expires: int = DAY,
    ):
        return self._make_get_object(object_name, version).presigned_url(
            expires
        )

    def object_info(
        self,
        object_name: str,
        version: Optional[str] = None,
    ):
        return self._make_get_object(object_name, version).info()

    def _make_get_object(
        self, object_name: str, version: Optional[str] = None
    ):
        return HandleObject(self.core, object_name, version)
