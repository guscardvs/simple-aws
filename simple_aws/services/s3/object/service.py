from dataclasses import dataclass
from dataclasses import field
from typing import Callable
from typing import Optional
from typing import TypeVar

from gyver.utils import lazyfield
from typing_extensions import Concatenate
from typing_extensions import ParamSpec

from simple_aws.config import make_default_factory
from simple_aws.credentials import Credentials
from simple_aws.services.s3.config import S3ObjectConfig
from simple_aws.services.s3.object.copy import Copy
from simple_aws.services.s3.object.copy import CopyParams

from .core import S3Core
from .delete import DeleteMany
from .delete import ObjectTuple
from .get import DAY
from .get import Get
from .list_ import MAX_CHUNKSIZE
from .list_ import List
from .upload import Upload

P = ParamSpec("P")
T = TypeVar("T")


@dataclass(frozen=True)
class S3Object:
    credentials: Credentials
    config: S3ObjectConfig = field(
        default_factory=make_default_factory(S3ObjectConfig)
    )

    @lazyfield
    def core(self):
        return S3Core(self.credentials, self.config)

    def build(
        self,
        cls: Callable[Concatenate[S3Core, P], T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        return cls(self.core, *args, **kwargs)

    def upload(
        self,
        object_name: str,
        content: bytes,
        *,
        content_type: Optional[str] = None
    ) -> None:
        return self.build(Upload, object_name, content, content_type).upload()

    def list_objects(
        self,
        prefix: Optional[str] = None,
        chunksize: int = MAX_CHUNKSIZE,
    ):
        return self.build(List, prefix, chunksize)

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

    def delete(self, object_name: str, version: Optional[str] = None):
        return self.build(
            DeleteMany, (ObjectTuple(object_name, version),)
        ).delete()

    def delete_many(self, *objects: ObjectTuple):
        return self.build(DeleteMany, objects).delete()

    def _make_get_object(
        self, object_name: str, version: Optional[str] = None
    ):
        return self.build(Get, object_name, version)

    def copy(
        self, source: CopyParams, target: CopyParams, prevalidate: bool = True
    ):
        return self.build(Copy, prevalidate).copy(source, target)

    def copy_from(
        self,
        source: CopyParams,
        target_name: Optional[str] = None,
        prevalidate: bool = True,
    ):
        return self.build(Copy, prevalidate).copy_from(source, target_name)

    def copy_to(
        self,
        target: CopyParams,
        source_name: Optional[str] = None,
        prevalidate: bool = True,
    ):
        return self.build(Copy, prevalidate).copy_to(target, source_name)

    def move(
        self, object_name: str, destination: str, prevalidate: bool = True
    ):
        """Move an object inside the same bucket
        destination and object_name must be the full object path"""
        with self.core.context.open():
            self.copy_in_bucket(object_name, destination, prevalidate)
            self.delete(object_name)

    def copy_in_bucket(
        self, object_name: str, destination: str, prevalidate: bool = True
    ):
        """Copy an object inside the same bucket
        destination and object_name must be the full object path"""
        self.copy_to(
            CopyParams(destination, self.core.config.bucket_name),
            object_name,
            prevalidate,
        )
