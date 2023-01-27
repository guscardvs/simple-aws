from gyver.config import ProviderConfig


class Credentials(ProviderConfig):
    __prefix__ = "aws"

    access_key_id: str
    secret_access_key: str
    region: str
    host: str = ""
