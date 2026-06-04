from enum import Enum
from typing import get_args as typing_get_args
from typing import List
from typing import Literal
from typing import Optional
from pydantic import BaseModel
from pydantic import StrictStr

from catweazle.model.v2.common import ModelV2MetaMulti

filter_literal = Literal[
    "id",
    "ldap_group",
    "permissions",
    "users",
]

filter_list = set(typing_get_args(filter_literal))

sort_literal = Literal["id"]


class ModelV2Permission(str, Enum):
    INSTANCE_DELETE = "INSTANCE:DELETE"
    INSTANCE_POST = "INSTANCE:POST"
    WEBHOOK_DELETE = "WEBHOOK:DELETE"
    WEBHOOK_POST = "WEBHOOK:POST"
    SECRET_DELETE = "SECRET:DELETE"
    SECRET_POST = "SECRET:POST"
    WEBHOOK_LOG_GET = "WEBHOOK_LOG:GET"


class ModelV2PermissionGet(BaseModel):
    id: Optional[StrictStr] = None
    ldap_group: Optional[StrictStr] = ""
    permissions: Optional[List[ModelV2Permission]] = None
    users: Optional[List[StrictStr]] = None


class ModelV2PermissionGetMulti(BaseModel):
    result: List[ModelV2PermissionGet]
    meta: ModelV2MetaMulti


class ModelV2PermissionPost(BaseModel):
    ldap_group: Optional[StrictStr] = ""
    permissions: Optional[List[ModelV2Permission]] = None
    users: Optional[List[StrictStr]] = []


class ModelV2PermissionPut(BaseModel):
    ldap_group: Optional[StrictStr] = None
    permissions: Optional[List[ModelV2Permission]] = None
    users: Optional[List[StrictStr]] = None
