from typing import get_args as typing_get_args
from typing import Literal
from pydantic import BaseModel

from catweazle.model.v2.instances import ModelV2InstanceGet
from catweazle.config import Config

config = Config()

filter_literal = Literal[
    "id",
    "dns_indicator",
    "fqdn",
    "ip_address",
    "ipa_otp",
]

filter_list = set(typing_get_args(filter_literal))

sort_literal = Literal[
    "id",
    "dns_indicator",
    "fqdn",
    "ip_address",
]


class ModelV1InstanceGet(BaseModel):
    data: ModelV2InstanceGet
