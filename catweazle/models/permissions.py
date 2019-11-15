__author__ = 'schlitzer'

import pymongo
import pymongo.errors

from catweazle.models.mixins import Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn
from catweazle.models.mixins import pagination_from_schema
from catweazle.models.mixins import projection_from_schema
from catweazle.models.mixins import sort_from_schema
from catweazle.errors import MongoConnError, PermError, ResourceNotFound, DuplicateResource
from catweazle.schemes import schemes


class Permissions(Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn):
    def __init__(self, coll):
        super().__init__()
        self.pagination_steps = pagination_from_schema(
            schema=schemes, path='/permissions/_search'
        )
        self.pagination_limit = self.pagination_steps[-1]
        self.projection_fields = projection_from_schema(
            schema=schemes, path='/permissions/_search'
        )
        self.sort_fields = sort_from_schema(
            schema=schemes, path='/permissions/_search'
        )
        self._coll = coll

    async def check(self, user, fields, permission):
        query = {
            'deleting': False,
            'users': user
        }
        self._filter_list(query, 'permissions', permission)
        try:
            result = await self._coll.find_one(
                filter=query,
                projection=self._projection(fields)
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise PermError(
                msg="Required Permissions {0} not found for user {1}".format(
                    permission, user
                )
            )
        return result

    async def create(self, _id, payload):
        payload['id'] = _id
        payload['deleting'] = False
        try:
            await self._coll.insert_one(payload)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateResource(_id)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        return await self.get(_id)

    async def delete(self, _id):
        try:
            result = await self._coll.delete_one(filter={
                'id': _id,
            })
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result.deleted_count is 0:
            raise ResourceNotFound(_id)
        return

    async def delete_mark(self, _id):
        update = {'$set': {'deleting': True}}
        try:
            await self._coll.update_one(
                filter={'id': _id},
                update=update,
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def get(self, _id, fields=None):
        try:
            result = await self._coll.find_one(
                filter={
                    'id': _id,
                    'deleting': False
                },
                projection=self._projection(fields)
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        return self._format(result)

    async def delete_user_from_all(self, user):
        try:
            await self._coll.update_many(
                filter={"users": user},
                update={"$pull": {"users": user}}
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def search(
            self, permission, permissions=None, users=None,
            fields=None, sort=None, page=None, limit=None):
        query = {}
        self._filter_re(query, 'id', permission)
        self._filter_re(query, 'permissions', permissions)
        self._filter_re(query, 'users', users)
        self._filter_boolean(query, 'deleting', False)
        try:
            cursor = self._coll.find(
                filter=query,
                projection=self._projection(fields)
            )
            cursor.sort(self._sort(sort))
            cursor.skip(self._pagination_skip(page, limit))
            cursor.limit(self._pagination_limit(limit))
            result = list()
            for item in await cursor.to_list(self._pagination_limit(limit)):
                result.append(self._format(item))
            return self._format(result, multi=True)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def update(self, _id, payload):
        update = {'$set': {}}
        for k, v in payload.items():
            update['$set'][k] = v
        try:
            result = await self._coll.find_one_and_update(
                filter={'id': _id},
                update=update,
                projection=self._projection(),
                return_document=pymongo.ReturnDocument.AFTER
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        return self._format(result)
