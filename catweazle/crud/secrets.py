import base64
from datetime import datetime
from datetime import UTC
import hashlib
import logging
import typing

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo

from catweazle.crud.common import CrudMongo
from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.secrets import ModelV2SecretGet
from catweazle.model.v2.secrets import ModelV2SecretGetMulti
from catweazle.model.v2.secrets import ModelV2SecretPost
from catweazle.model.v2.secrets import ModelV2SecretPut


class CrudSecrets(CrudMongo):
    def __init__(self, log: logging.Logger, coll: AsyncIOMotorCollection, encryption_key: str):
        super(CrudSecrets, self).__init__(log=log, coll=coll)
        key = base64.urlsafe_b64encode(hashlib.sha256(encryption_key.encode()).digest())
        self._fernet = Fernet(key)

    async def index_create(self) -> None:
        self.log.info(f"creating {self.resource_type} indices")
        await self.coll.create_index([("id", pymongo.ASCENDING)], unique=True)
        self.log.info(f"creating {self.resource_type} indices, done")

    def _encrypt(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()

    def _decrypt(self, data: str) -> str:
        return self._fernet.decrypt(data.encode()).decode()

    async def create(self, payload: ModelV2SecretPost, fields: list) -> ModelV2SecretGet:
        data = payload.model_dump()
        data["secret"] = self._encrypt(data["secret"])
        data["created"] = datetime.now(UTC)
        result = await self._create(payload=data, fields=fields)
        return ModelV2SecretGet(**result)

    async def delete(self, _id: str) -> ModelV2DataDelete:
        query = {"id": _id}
        await self._delete(query=query)
        return ModelV2DataDelete()

    async def get(self, _id: str, fields: list) -> ModelV2SecretGet:
        query = {"id": _id}
        result = await self._get(query=query, fields=fields)
        return ModelV2SecretGet(**result)

    async def get_secret(self, _id: str) -> str:
        query = {"id": _id}
        result = await self._get(query=query, fields=["secret"])
        return self._decrypt(result["secret"])

    async def search(
        self,
        _id: typing.Optional[str] = None,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
    ) -> ModelV2SecretGetMulti:
        query = {}
        self._filter_re(query, "id", _id)
        result = await self._search(
            query=query,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return ModelV2SecretGetMulti(
            result=result["result"],
            meta={"result_size": result["count"]}
        )

    async def update(
        self, _id: str, payload: ModelV2SecretPut, fields: list
    ) -> ModelV2SecretGet:
        query = {"id": _id}
        data = payload.model_dump(exclude_unset=True)
        if "secret" in data:
            data["secret"] = self._encrypt(data["secret"])
            data["created"] = datetime.now(UTC)
        result = await self._update(query=query, fields=fields, payload=data)
        return ModelV2SecretGet(**result)
