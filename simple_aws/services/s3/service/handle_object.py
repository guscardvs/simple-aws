from dataclasses import dataclass
from dataclasses import field

from furl.furl import furl
from gyver.context import Context
from gyver.utils import lazyfield
from requests import Session

from simple_aws.auth import AwsAuthV4
from simple_aws.config import make_default_factory
from simple_aws.credentials import Credentials
from simple_aws.http import HttpProvider
from simple_aws.services.s3.config import S3Config

HOST_TEMPLATE = "https://{bucket}.s3.{region}.amazonaws.com"
SERVICE_NAME = "s3"


@dataclass(frozen=True)
class S3Core:
    credentials: Credentials
    config: S3Config = field(default_factory=make_default_factory(S3Config))
    http_provider: HttpProvider = field(default_factory=HttpProvider)

    @lazyfield
    def base_uri(self) -> furl:
        return furl(
            HOST_TEMPLATE.format(
                bucket=self.config.bucket_name, region=self.credentials.region
            )
        )

    @lazyfield
    def aws_auth(self) -> AwsAuthV4:
        return AwsAuthV4(self.credentials, SERVICE_NAME)

    @lazyfield
    def context(self) -> Context[Session]:
        return Context(self.http_provider)
