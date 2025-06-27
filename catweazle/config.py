import typing

from pydantic import BaseModel
from pydantic import StrictStr
from pydantic import field_validator
from pydantic.networks import IPv4Network
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

log_levels = typing.Literal[
    "CRITICAL", "FATAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG"
]


class ConfigApp(BaseModel):
    loglevel: log_levels = "INFO"
    host: str = "127.0.0.1"
    port: int = 8000
    secretkey: str = "secret"
    indicator_regex: str = "^.*NUM.*$"
    domain_suffix: str = ".example.com"
    dry_run: bool = False


class ConfigLdap(BaseModel):
    url: typing.Optional[str] = None
    basedn: typing.Optional[str] = None
    binddn: typing.Optional[str] = None
    password: typing.Optional[str] = None
    userpattern: typing.Optional[str] = None


class ConfigMongodb(BaseModel):
    url: str = "mongodb://localhost:27017"
    database: str = "catweazle"


class ConfigOAuthClient(BaseModel):
    id: str
    secret: str


class ConfigOAuthUrl(BaseModel):
    authorize: str
    accesstoken: str
    userinfo: typing.Optional["str"] = None


class ConfigOAuth(BaseModel):
    override: bool = False
    scope: str
    type: str
    client: ConfigOAuthClient
    url: ConfigOAuthUrl


class ConfigForeman(BaseModel):
    url: StrictStr
    sslcrt: typing.Optional[StrictStr] = None
    sslkey: typing.Optional[StrictStr] = None
    dnsforwardenable: bool = False
    dnsarpaenable: bool = False
    dnsarpazones: typing.Optional[typing.List[IPv4Network]] = []
    realmenable: bool = False
    realmname: typing.Optional[StrictStr] = None

    @field_validator("dnsarpazones", mode="before")
    def validate_dns_indicator(v):
        networks = list()
        for network in v.split():
            try:
                networks.append(IPv4Network(network.strip()))
            except ValueError as e:
                raise ValueError(f"Invalid IPv4 network: {network}") from e
        return networks


class Config(BaseSettings):
    app: ConfigApp = ConfigApp()
    ldap: ConfigLdap = ConfigLdap()
    mongodb: ConfigMongodb = ConfigMongodb()
    foreman: typing.Optional[dict[str, ConfigForeman]] = None
    oauth: typing.Optional[dict[str, ConfigOAuth]] = None
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="_")
