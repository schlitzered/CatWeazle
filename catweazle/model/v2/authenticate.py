from pydantic import BaseModel


class ModelV2AuthenticateGetUser(BaseModel):
    user: str


class ModelV2AuthenticatePost(ModelV2AuthenticateGetUser):
    password: str
