__author__ = 'schlitzer'

import datetime
import random
import string
import uuid

from bson.binary import Binary, STANDARD
from passlib.hash import pbkdf2_sha512
import pymongo
import pymongo.errors

from catweazle.models.mixins import ProjectionMixIn
from catweazle.models.mixins import FilterMixIn
from catweazle.models.mixins import Format
from catweazle.models.mixins import ID
from catweazle.errors import CredentialError, MongoConnError, ResourceNotFound


class Credentials(Format, FilterMixIn, ProjectionMixIn, ID):
    def __init__(self, coll):
        super().__init__()
        self.projection_fields = {
            'id': 1,
            'created': 1,
            'description': 1
        }
        self._coll = coll

    @staticmethod
    def _create_secret(token):
        return pbkdf2_sha512.encrypt(str(token), rounds=10, salt_size=32)

    async def check_credential(self, credentials):
        try:
            result = await self._coll.find_one(
                filter={
                    'id': self._str_uuid_2_bin(credentials['id'])
                },
            )
            if not result:
                raise CredentialError
            if not pbkdf2_sha512.verify(credentials['secret'], result['secret']):
                raise CredentialError
            return self._format({'user': result['owner']})
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def create(self, owner, payload):
        _id = uuid.uuid4()
        secret = ''.join(random.SystemRandom().choice(
            string.ascii_letters + string.digits + '_-.') for _ in range(128))
        created = datetime.datetime.utcnow()
        payload['id'] = Binary(_id.bytes, STANDARD)
        payload['secret'] = self._create_secret(str(secret))
        payload['created'] = created
        payload['owner'] = owner
        try:
            await self._coll.insert_one(payload)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        result = {
            'id': str(_id),
            'created': str(created),
            'description': payload['description'],
            'secret': str(secret)
        }
        return self._format(result)

    async def delete(self, _id, owner):
        try:
            result = await self._coll.delete_one(
                filter={
                    'id': self._str_uuid_2_bin(_id),
                    'owner': owner
                }
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result.deleted_count is 0:
            raise ResourceNotFound(_id)
        return

    async def delete_all_from_owner(self, owner):
        try:
            await self._coll.delete_many(
                filter={"owner": owner}
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def get(self, _id, owner):
        try:
            result = await self._coll.find_one(
                filter={
                    'id': self._str_uuid_2_bin(_id),
                    'owner': owner}
                ,
                projection=self._projection()
            )
            if result is None:
                raise ResourceNotFound(_id)
            if 'created' in result:
                result['created'] = str(result['created'])
            if 'id' in result:
                result['id'] = str(result['id'])
            return self._format(result)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def get_all(self, owner):
        try:
            cursor = self._coll.find(
                filter={'owner': owner},
                projection=self._projection()
            )
            result = list()
            for item in await cursor.to_list(1000):
                if 'created' in item:
                    item['created'] = str(item['created'])
                if 'id' in item:
                    item['id'] = str(item['id'])
                result.append(self._format(item))
            return self._format(result, multi=True)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)

    async def update(self, _id, owner, payload):
        update = {'$set': {}}
        for k, v in payload.items():
            update['$set'][k] = v
        try:
            result = await self._coll.find_one_and_update(
                filter={
                    'id': self._str_uuid_2_bin(_id),
                    'owner': owner
                },
                update=update,
                projection=self._projection(),
                return_document=pymongo.ReturnDocument.AFTER
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        if 'created' in result:
            result['created'] = str(result['created'])
        if 'id' in result:
            result['id'] = str(result['id'])
        return self._format(result)
