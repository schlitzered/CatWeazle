import logging
import typing
from datetime import datetime
from datetime import timezone

from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo
import pymongo.errors

from catweazle.crud.common import CrudMongo

from catweazle.errors import BackendError

from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.webhook_logs import ModelV2WebhookLogGet
from catweazle.model.v2.webhook_logs import ModelV2WebhookLogGetMulti


class CrudWebhookLogs(CrudMongo):
    def __init__(
        self,
        log: logging.Logger,
        coll: AsyncIOMotorCollection,
        ttl: int = 86400,
    ):
        super(CrudWebhookLogs, self).__init__(log=log, coll=coll)
        self._ttl = ttl

    @property
    def ttl(self):
        return self._ttl

    async def index_create(self) -> None:
        self.log.info(f"creating {self.resource_type} indices")
        await self.coll.create_index(
            [("created_at", pymongo.ASCENDING)],
            expireAfterSeconds=self.ttl,
        )
        self.log.info(f"creating {self.resource_type} indices, done")

    async def create(
        self,
        instance_id: str,
        webhook_id: str,
        trigger: str,
        url: str,
        method: str,
        request_headers: dict = None,
        request_params: dict = None,
        request_body: dict = None,
        response_status_code: int = None,
        response_headers: dict = None,
        response_body: str = None,
        error: str = None,
    ) -> ModelV2WebhookLogGet:
        payload = {
            "instance_id": instance_id,
            "webhook_id": webhook_id,
            "trigger": trigger,
            "url": url,
            "method": method,
            "request_headers": request_headers,
            "request_params": request_params,
            "request_body": request_body,
            "response_status_code": response_status_code,
            "response_headers": response_headers,
            "response_body": response_body,
            "error": error,
            "created_at": datetime.now(tz=timezone.utc),
        }
        try:
            await self._coll.insert_one(payload)
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError()
        return ModelV2WebhookLogGet(**self._format(payload))

    async def search(
        self,
        instance_id: typing.Optional[str] = None,
        webhook_id: typing.Optional[str] = None,
        trigger: typing.Optional[str] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
    ) -> ModelV2WebhookLogGetMulti:
        query = {}
        self._filter_re(query, "instance_id", instance_id)
        self._filter_re(query, "webhook_id", webhook_id)
        self._filter_re(query, "trigger", trigger)
        result = await self._search(
            query=query,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return ModelV2WebhookLogGetMulti(**result)
