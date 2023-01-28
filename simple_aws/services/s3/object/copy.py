from dataclasses import dataclass
from typing import NamedTuple
from typing import Optional

from gyver.url import URL
from gyver.url import Path

from simple_aws.exc import RequestFailed
from simple_aws.services.s3.config import S3ObjectConfig
from simple_aws.services.s3.object.core import HOST_TEMPLATE
from simple_aws.services.s3.object.core import S3Core
from simple_aws.services.s3.object.get import Get


class CopyParams(NamedTuple):
    object_name: str
    bucket: str


@dataclass(frozen=True)
class Copy:
    core: S3Core
    prevalidate: bool = True

    def copy(self, source: CopyParams, target: CopyParams):
        url = URL(
            HOST_TEMPLATE.format(
                bucket=target.bucket, region=self.core.credentials.region
            )
        ).add(path=target.object_name)

        if self.prevalidate:
            # validate if source object exists
            Get(
                S3Core(
                    self.core.credentials,
                    S3ObjectConfig(bucket_name=source.bucket),
                ),
                source.object_name,
            ).info()
        with self.core.context.begin() as client:
            response = client.put(
                url,
                headers={
                    "x-amz-copy-source": Path(source.bucket)
                    .add(source.object_name)
                    .encode()
                },
            )
            if not response.ok:
                raise RequestFailed(response)

    def copy_from(self, source: CopyParams, target_name: Optional[str] = None):
        target = CopyParams(
            target_name or source.object_name, self.core.config.bucket_name
        )
        return self.copy(source, target)

    def copy_to(self, target: CopyParams, source_name: Optional[str] = None):
        source = CopyParams(
            source_name or target.object_name, self.core.config.bucket_name
        )
        return self.copy(source, target)
