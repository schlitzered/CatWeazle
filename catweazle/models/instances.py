__author__ = 'schlitzer'

import pymongo
import pymongo.errors

from catweazle.models.mixins import Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn
from catweazle.models.mixins import pagination_from_schema
from catweazle.models.mixins import projection_from_schema
from catweazle.models.mixins import sort_from_schema
from catweazle.errors import MongoConnError, ResourceNotFound, DuplicateResource
from catweazle.schemes import schemes


class Instances(Format, FilterMixIn, PaginationSkipMixIn, ProjectionMixIn, SortMixIn):
    def __init__(self, coll, domain_suffix):
        super().__init__()
        self.pagination_steps = pagination_from_schema(
            schema=schemes, path='/instances/_search'
        )
        self.pagination_limit = self.pagination_steps[-1]
        self.projection_fields = projection_from_schema(
            schema=schemes, path='/instances/_search'
        )
        self.sort_fields = sort_from_schema(
            schema=schemes, path='/instances/_search'
        )
        self._domain_suffix = domain_suffix
        self._coll = coll

    @property
    def domain_suffix(self):
        return self._domain_suffix

    async def _next_num(self, indicator):
        instances = await self.search(dns_indicator=indicator)
        taken = list()
        for instance in instances['data']['results']:
            taken.append(instance['data']['fqdn'])

        fqdn = "{0}{1}".format(indicator, self.domain_suffix)
        for number in range(1, 1000):
            number = str(number)
            if fqdn.replace('NUM', number) not in taken:
                return number

    async def create(self, _id, payload):
        payload['id'] = _id
        fqdn = "{0}{1}".format(payload['dns_indicator'], self.domain_suffix)
        if 'NUM' in payload['dns_indicator']:
            number = await self._next_num(payload['dns_indicator'])
            fqdn = fqdn.replace('NUM', number)
        payload['fqdn'] = fqdn
        try:
            await self._coll.insert_one(payload)
        except pymongo.errors.DuplicateKeyError:
            raise DuplicateResource(_id)
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        return await self.get(_id)

    async def set_ipa_otp(self, _id, ipa_otp):
        if not ipa_otp:
            ipa_otp = ""
        update = {'$set': {}}
        update['$set']['ipa_otp'] = ipa_otp
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

    async def get(self, _id, fields=None):
        try:
            result = await self._coll.find_one(
                filter={
                    'id': _id,
                },
                projection=self._projection(fields)
            )
        except pymongo.errors.ConnectionFailure as err:
            raise MongoConnError(err)
        if result is None:
            raise ResourceNotFound(_id)
        return self._format(result)

    async def search(
            self,  instances=None, dns_indicator=None, fqdn=None, ip_address=None,
            fields=None, sort=None, page=None, limit=None):
        query = {}
        self._filter_re(query, 'id', instances)
        self._filter_re(query, 'dns_indicator', dns_indicator)
        self._filter_re(query, 'fqdn', fqdn)
        self._filter_re(query, 'ip_address', ip_address)
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
