import re
from typing import Literal
from typing import Set

from pydantic import BaseModel
from pydantic import constr
from pydantic import Field
from typing_extensions import Annotated


sort_order_literal = Literal[
    "ascending",
    "descending",
]


class ModelV2MetaMulti(BaseModel):
    result_size: Annotated[int, Field(gt=-1)]


class ModelV2DataDelete(BaseModel):
    pass
