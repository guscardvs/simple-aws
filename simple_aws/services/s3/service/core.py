from dataclasses import dataclass
from dataclasses import field

from furl.furl import furl
from gyver.context import Context
from gyver.utils import lazyfield

from simple_aws.auth import AwsAuthV4
from simple_aws.config import make_default_factory
from simple_aws.credentials import Credentials
from simple_aws.http import AuthHttpAdapter
from simple_aws.http import AuthHttpClient
from simple_aws.services.s3.config import S3Config

HOST_TEMPLATE = "https://{bucket}.s3.{region}.amazonaws.com"
SERVICE_NAME = "s3"


@dataclass(frozen=True)
class S3Core:
    credentials: Credentials
    config: S3Config = field(default_factory=make_default_factory(S3Config))

    @lazyfield
    def base_uri(self) -> furl:
        return furl(
            HOST_TEMPLATE.format(
                bucket=self.config.bucket_name, region=self.credentials.region
            )
        )

    def get_uri_copy(self):
        return self.base_uri.copy()

    @lazyfield
    def aws_auth(self) -> AwsAuthV4:
        return AwsAuthV4(self.credentials, SERVICE_NAME)

    @lazyfield
    def http_provider(self):
        return AuthHttpAdapter(self.credentials, SERVICE_NAME)

    @lazyfield
    def context(self) -> Context[AuthHttpClient]:
        return Context(self.http_provider)
