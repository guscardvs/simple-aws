from typing import Callable
from typing import Optional
from typing import TypeVar

from gyver.config import ConfigLoader
from typing_extensions import Concatenate
from typing_extensions import ParamSpec

from simple_aws.config import ProviderConfigT
from simple_aws.credentials import Credentials

from . import s3

T = TypeVar("T")
P = ParamSpec("P")


class ServiceFactory:
    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        config_loader: Optional[ConfigLoader] = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.credentials = credentials or self.config_loader.load(Credentials)

    def build(
        self,
        service_class: Callable[Concatenate[Credentials, P], T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        return service_class(self.credentials, *args, **kwargs)

    def s3_object(
        self, config: Optional[s3.S3ObjectConfig] = None
    ) -> s3.S3Object:
        return self.build(
            s3.S3Object, config=self.get_or_load(s3.S3ObjectConfig, config)
        )

    def get_or_load(
        self,
        config_class: type[ProviderConfigT],
        value: Optional[ProviderConfigT],
    ) -> ProviderConfigT:
        return value or self.config_loader.load(config_class)
