import re
from typing import get_args as typing_get_args
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional
from pydantic import BaseModel
from pydantic import StrictStr
from pydantic import field_validator
from pydantic.networks import IPv4Address

from catweazle.model.v2.common import ModelV2MetaMulti
from catweazle.config import Config

config = Config()

filter_literal = Literal[
    "id",
    "dns_indicator",
    "fqdn",
    "ip_address",
    "ipa_otp",
    "meta",
]

filter_list = set(typing_get_args(filter_literal))

sort_literal = Literal[
    "id",
    "dns_indicator",
    "fqdn",
    "ip_address",
]


class ModelV2InstanceGet(BaseModel):
    id: Optional[StrictStr] = None
    dns_indicator: Optional[StrictStr] = None
    fqdn: Optional[StrictStr] = None
    ip_address: Optional[StrictStr] = None
    ipa_otp: Optional[StrictStr] = None
    meta: Optional[Dict[str, str]] = None


class ModelV2InstanceGetMulti(BaseModel):
    result: List[ModelV2InstanceGet]
    meta: ModelV2MetaMulti


class ModelV2instancePost(BaseModel):
    dns_indicator: Optional[StrictStr] = None
    ip_address: IPv4Address
    meta: Optional[Dict[str, str]] = None

    @staticmethod
    @field_validator("dns_indicator", mode="before")
    def validate_dns_indicator(value):
        regex = re.compile(config.app.indicator_regex)
        if not regex.match(value):
            raise ValueError(
                f"dns_indicator does not match regex: {config.app.indicator_regex}"
            )
        return value

class ModelV2instancePut(BaseModel):
    meta: Optional[Dict[str, str]] = None
