__author__ = 'schlitzer'

from passlib.hash import pbkdf2_sha512
import pymongo
import pymongo.errors

from catweazle.models.mixins import Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn
from catweazle.models.mixins import pagination_from_schema
from catweazle.models.mixins import projection_from_schema
from catweazle.models.mixins import sort_from_schema
from catweazle.errors import AuthenticationError, MongoConnError, DuplicateResource, ResourceNotFound
from catweazle.schemes import schemes


class Users(Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn):
    def __init__(self, coll):
        super().__init__()
        self.pagination_steps = pagination_from_schema(
            schema=schemes, path='/users/_search'
        )
        self.pagination_limit = self.pagination_steps[-1]
        self.projection_fields = projection_from_schema(
            schema=schemes, path='/users/_search'
        )
        self.sort_fields = sort_from_schema(
            schema=schemes, path='/users/_search'
        )
        self._coll = coll

    @staticmethod
    async def _password(password):
        return pbkdf2_sha512.encrypt(password, rounds=100000, salt_size=32)

    async def check_credentials(self, credentials):
        try:
            password = await self._coll.find_one(
                filter={'id': credentials['user'], 'deleting': False},
                projection={'password': 1}
            )
            if not password:
                raise AuthenticationError
            if not pbkdf2_sha512.verify(credentials['password'], password['password']):
                raise AuthenticationError
            return credentials['user']
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def create(self, _id, payload):
        payload['password'] = await self._password(payload['password'])
        payload['deleting'] = False
        payload['id'] = _id
        try:
            await self._coll.insert_one(payload)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateResource(_id)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        return await self.get(_id)

    async def delete(self, _id):
        try:
            result = await self._coll.delete_one(filter={'id': _id})
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
                filter={'id': _id, 'deleting': False},
                projection=self._projection(fields)
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        return self._format(result)

    async def is_admin(self, user):
        resource = await self.get(user, fields='admin')
        if not resource['data']['admin']:
            return False
        return True

    async def search(self, _id=None, fields=None, sort=None, page=None, limit=None):
        query = {'deleting': False}
        self._filter_re(query, 'id', _id)
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
        if 'password' in payload:
            payload['password'] = await self._password(payload['password'])
        update = {'$set': {}}
        for k, v in payload.items():
            update['$set'][k] = v
        try:
            result = await self._coll.find_one_and_update(
                filter={'id': _id, 'deleting': False},
                update=update,
                projection=self._projection(),
                return_document=pymongo.ReturnDocument.AFTER
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        return self._format(result)

    async def resource_exists(self, _id):
        try:
            await self.get(_id=_id, fields='id')
            return True
        except ResourceNotFound:
            return False
