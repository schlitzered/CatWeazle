from typing import get_args as typing_get_args
from typing import Optional
from typing import List
from typing import Literal

from pydantic import BaseModel

from catweazle.model.v2.common import ModelV2MetaMulti

filter_literal = Literal[
    "id",
    "created",
    "description",
]

filter_list = set(typing_get_args(filter_literal))

sort_literal = Literal[
    "id",
    "created",
]


class ModelV2CredentialGet(BaseModel):
    id: Optional[str] = None
    created: Optional[str] = None
    description: Optional[str] = None


class ModelV2CredentialGetMulti(BaseModel):
    result: List[ModelV2CredentialGet]
    meta: ModelV2MetaMulti


class ModelV2CredentialPost(BaseModel):
    description: str


class ModelV2CredentialPostResult(ModelV2CredentialGet):
    secret: str


class ModelV2CredentialPut(BaseModel):
    description: str
