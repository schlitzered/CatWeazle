from pydantic import BaseModel


class ModelApiVersions(BaseModel):
    version: str
