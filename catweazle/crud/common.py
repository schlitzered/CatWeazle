import logging
import typing

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo
import pymongo.errors

from catweazle.crud.mixins import FilterMixIn
from catweazle.crud.mixins import Format
from catweazle.crud.mixins import PaginationSkipMixIn
from catweazle.crud.mixins import ProjectionMixIn
from catweazle.crud.mixins import SortMixIn

from catweazle.errors import DuplicateResource
from catweazle.errors import ResourceNotFound
from catweazle.errors import BackendError


class Crud:
    def __init__(self, log: logging.Logger):
        self._log = log

    @property
    def log(self):
        return self._log


class CrudMongo(
    Crud, FilterMixIn, Format, PaginationSkipMixIn, ProjectionMixIn, SortMixIn
):
    def __init__(self, log: logging.Logger, coll: AsyncIOMotorCollection):
        super().__init__(log)
        self._resource_type = coll.name
        self._coll = coll

    @property
    def coll(self):
        return self._coll

    @property
    def resource_type(self):
        return self._resource_type

    async def _create(
        self,
        payload: dict,
        fields: list = None,
    ) -> dict:
        try:
            _id = await self._coll.insert_one(payload)
            return await self._get_by_obj_id(_id=_id.inserted_id, fields=fields)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateResource
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError()

    async def _delete(self, query: dict) -> dict:
        try:
            result = await self._coll.delete_one(filter=query)
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError()
        if result.deleted_count == 0:
            raise ResourceNotFound
        return {}

    async def _get(self, query: dict, fields: list) -> dict:
        try:
            result = await self._coll.find_one(
                filter=query, projection=self._projection(fields)
            )
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError
        if result is None:
            if "$and" in query:
                query = query["$and"][0]
            raise ResourceNotFound(
                details=f"Resource {self.resource_type} {query} not found"
            )
        return self._format(result)

    async def _get_by_obj_id(self, _id, fields: list) -> dict:
        query = {"_id": _id}
        return await self._get(query=query, fields=fields)

    async def _resource_exists(self, query: dict) -> ObjectId:
        result = await self._get(query=query, fields=["id"])
        return result["id"]

    async def _search(
        self,
        query: dict,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[str] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
    ) -> dict:
        try:
            count = await self._coll.count_documents(
                filter=query,
            )
            cursor = self._coll.find(filter=query, projection=self._projection(fields))
            if sort and sort_order:
                cursor.sort(self._sort(sort=sort, sort_order=sort_order))
            if page and limit:
                cursor.skip(self._pagination_skip(page, limit))
                cursor.limit(limit)
            return self._format_multi(list(await cursor.to_list(limit)), count=count)
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError

    async def _update(
        self, query: dict, payload: dict, fields: list, upsert=False
    ) -> dict:
        update = {"$set": {}}
        for k, v in payload.items():
            if v is None:
                continue
            update["$set"][k] = v
        try:
            result = await self._coll.find_one_and_update(
                filter=query,
                update=update,
                projection=self._projection(fields=fields),
                return_document=pymongo.ReturnDocument.AFTER,
                upsert=upsert,
            )
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError
        if result is None:
            raise ResourceNotFound
        return self._format(result)
