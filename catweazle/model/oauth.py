from typing import List
from typing import Optional
from pydantic import BaseModel
from pydantic import StrictStr

from catweazle.model.v2.common import ModelV2MetaMulti


class ModelOauthProviderGet(BaseModel):
    id: Optional[StrictStr] = None


class ModelOauthProviderGetMulti(BaseModel):
    result: List[ModelOauthProviderGet]
    meta: ModelV2MetaMulti
