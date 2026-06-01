from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel

from catweazle.model.v2.common import ModelV2MetaMulti


class ModelV2WebhookLogGet(BaseModel):
    instance_id: str
    webhook_id: str
    trigger: str
    url: str
    method: str
    request_headers: Optional[Dict[str, str]] = None
    request_params: Optional[Dict[str, str]] = None
    request_body: Optional[Dict[str, Any]] = None
    response_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


class ModelV2WebhookLogGetMulti(BaseModel):
    result: List[ModelV2WebhookLogGet]
    meta: ModelV2MetaMulti
