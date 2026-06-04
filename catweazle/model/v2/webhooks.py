from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

from pydantic import BaseModel

from catweazle.model.v2.common import ModelV2MetaMulti

webhook_methods = Literal["GET", "POST", "PUT", "DELETE"]
webhook_triggers = Literal["pre-create", "post-create", "pre-delete", "post-delete"]


class ModelV2WebhookPost(BaseModel):
    id: str
    url: str
    method: webhook_methods
    triggers: List[webhook_triggers]
    query_params: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    payload: Optional[Dict[str, Any]] = None
    fail_on_error: bool = False
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_ca: Optional[str] = None


class ModelV2WebhookPut(BaseModel):
    url: Optional[str] = None
    method: Optional[webhook_methods] = None
    triggers: Optional[List[webhook_triggers]] = None
    query_params: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None
    payload: Optional[Dict[str, Any]] = None
    fail_on_error: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_key: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_ca: Optional[str] = None


class ModelV2WebhookGet(ModelV2WebhookPost):
    pass


class ModelV2WebhookGetMulti(BaseModel):
    result: List[ModelV2WebhookGet]
    meta: ModelV2MetaMulti
