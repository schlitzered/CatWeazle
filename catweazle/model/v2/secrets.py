from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel

from catweazle.model.v2.common import ModelV2MetaMulti


class ModelV2SecretPost(BaseModel):
    id: str
    secret: str
    description: Optional[str] = None


class ModelV2SecretPut(BaseModel):
    secret: Optional[str] = None
    description: Optional[str] = None


class ModelV2SecretGet(BaseModel):
    id: str
    description: Optional[str] = None
    created: datetime


class ModelV2SecretGetMulti(BaseModel):
    result: List[ModelV2SecretGet]
    meta: ModelV2MetaMulti
