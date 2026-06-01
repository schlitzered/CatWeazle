import logging
import typing
import base64
import hashlib

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo

from catweazle.crud.common import CrudMongo
from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.webhooks import ModelV2WebhookGet
from catweazle.model.v2.webhooks import ModelV2WebhookGetMulti
from catweazle.model.v2.webhooks import ModelV2WebhookPost
from catweazle.model.v2.webhooks import ModelV2WebhookPut


class CrudWebhooks(CrudMongo):

    def __init__(
        self,
        *,
        log: logging.Logger,
        coll: AsyncIOMotorCollection,
        encryption_key: str,
    ):
        super().__init__(
            log=log,
            coll=coll,
        )
        key = base64.urlsafe_b64encode(
            hashlib.sha256(
                encryption_key.encode(),
            ).digest(),
        )
        self._fernet = Fernet(
            key=key,
        )

    def decrypt(
        self,
        *,
        data: str,
    ) -> str:
        if not data:
            return data
        return self._fernet.decrypt(
            data.encode(),
        ).decode()

    def _encrypt(
        self,
        *,
        data: str,
    ) -> str:
        if not data:
            return data
        return self._fernet.encrypt(
            data.encode(),
        ).decode()

    async def index_create(self) -> None:
        self.log.info(
            f"creating {self.resource_type} indices",
        )
        index_keys = [
            ("id", pymongo.ASCENDING),
        ]
        await self.coll.create_index(
            keys=index_keys,
            unique=True,
        )
        self.log.info(
            f"creating {self.resource_type} indices, done",
        )

    async def create(
        self,
        *,
        payload: ModelV2WebhookPost,
        fields: list,
    ) -> ModelV2WebhookGet:
        data = payload.model_dump()
        password = data.get("password")
        if password:
            data["password"] = self._encrypt(
                data=password,
            )
        ssl_key = data.get("ssl_key")
        if ssl_key:
            data["ssl_key"] = self._encrypt(
                data=ssl_key,
            )
        result = await self._create(
            payload=data,
            fields=fields,
        )
        return ModelV2WebhookGet(
            **result,
        )

    async def delete(
        self,
        *,
        _id: str,
    ) -> ModelV2DataDelete:
        query = {
            "id": _id,
        }
        await self._delete(
            query=query,
        )
        return ModelV2DataDelete()

    async def get(
        self,
        *,
        _id: str,
        fields: list,
    ) -> ModelV2WebhookGet:
        query = {
            "id": _id,
        }
        result = await self._get(
            query=query,
            fields=fields,
        )
        return ModelV2WebhookGet(
            **result,
        )

    async def search(
        self,
        *,
        _id: typing.Optional[str] = None,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        query: typing.Optional[dict] = None,
    ) -> ModelV2WebhookGetMulti:
        if not query:
            query = {}
        self._filter_re(
            query=query,
            field="id",
            selector=_id,
        )
        result = await self._search(
            query=query,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return ModelV2WebhookGetMulti(
            result=result["result"],
            meta={
                "result_size": result["count"],
            },
        )

    async def update(
        self,
        *,
        _id: str,
        payload: ModelV2WebhookPut,
        fields: list,
    ) -> ModelV2WebhookGet:
        query = {
            "id": _id,
        }
        data = payload.model_dump(
            exclude_unset=True,
        )
        password = data.get("password")
        if password:
            data["password"] = self._encrypt(
                data=password,
            )
        ssl_key = data.get("ssl_key")
        if ssl_key:
            data["ssl_key"] = self._encrypt(
                data=ssl_key,
            )
        result = await self._update(
            query=query,
            fields=fields,
            payload=data,
        )
        return ModelV2WebhookGet(
            **result,
        )
