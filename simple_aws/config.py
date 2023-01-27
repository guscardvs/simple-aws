from typing import Callable
from typing import TypeVar

from gyver.config import ConfigLoader
from gyver.config import ProviderConfig

default_loader = ConfigLoader()

ProviderConfigT = TypeVar("ProviderConfigT", bound=ProviderConfig)


def make_default_factory(
    config_class: type[ProviderConfigT],
) -> Callable[[], ProviderConfigT]:
    def factory():
        return default_loader.load(config_class)

    return factory
