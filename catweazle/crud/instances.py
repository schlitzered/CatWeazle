import logging
import typing

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo
import pymongo.errors

from catweazle.crud.common import CrudMongo

from catweazle.errors import HostNumRangeExceeded

from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.instances import ModelV2InstanceGet
from catweazle.model.v2.instances import ModelV2InstanceGetMulti
from catweazle.model.v2.instances import ModelV2instancePost
from catweazle.model.v2.instances import ModelV2instancePut


class CrudInstances(CrudMongo):
    def __init__(
        self, log: logging.Logger, coll: AsyncIOMotorCollection, domain_suffix: str
    ):
        super(CrudInstances, self).__init__(log=log, coll=coll)
        self._domain_suffix = domain_suffix

    @property
    def domain_suffix(self):
        return self._domain_suffix

    async def _next_num(self, indicator):
        instances = await self.search(dns_indicator=indicator)
        taken = list()
        for instance in instances.result:
            taken.append(instance.fqdn)

        fqdn = "{0}{1}".format(indicator, self.domain_suffix)
        host_max_range = 1000
        for number in range(1, host_max_range):
            number = str(number)
            if fqdn.replace("NUM", number) not in taken:
                return number
        raise HostNumRangeExceeded(max_range=host_max_range)

    async def index_create(self) -> None:
        self.log.info(f"creating {self.resource_type} indices")
        await self.coll.create_index([("id", pymongo.ASCENDING)], unique=True)
        await self.coll.create_index([("fqdn", pymongo.ASCENDING)], unique=True)
        self.log.info(f"creating {self.resource_type} indices, done")

    async def create(
        self, _id: str, payload: ModelV2instancePost, fields: list
    ) -> ModelV2InstanceGet:
        data = payload.model_dump()
        data["id"] = _id

        fqdn = f"{payload.dns_indicator}{self.domain_suffix}"
        if "NUM" in payload.dns_indicator:
            number = await self._next_num(payload.dns_indicator)
            fqdn = f"{payload.dns_indicator.replace('NUM', number)}{self.domain_suffix}"
        data["fqdn"] = fqdn
        data["ip_address"] = str(payload.ip_address)
        result = await self._create(fields=fields, payload=data)
        return ModelV2InstanceGet(**result)

    async def delete(
        self,
        _id: str,
    ) -> ModelV2DataDelete:
        query = {"id": _id}
        await self._delete(query=query)
        return ModelV2DataDelete()

    async def delete_mark(
        self,
        _id: str,
    ) -> None:
        query = {"id": _id}
        await self._delete_mark(query=query)

    async def get(
        self,
        _id: str,
        fields: list,
    ) -> ModelV2InstanceGet:
        query = {"id": _id}
        result = await self._get(
            query=query, fields=fields
        )
        return ModelV2InstanceGet(**result)

    async def resource_exists(
        self,
        _id: str,
    ) -> ObjectId:
        query = {"id": _id}
        return await self._resource_exists(query=query)

    async def search(
        self,
        _id: typing.Optional[str] = None,
        dns_indicator: typing.Optional[str] = None,
        ip_address: typing.Optional[str] = None,
        fqdn: typing.Optional[str] = None,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        query: typing.Optional[dict] = None,
    ) -> ModelV2InstanceGetMulti:
        if not query:
            query = {}
        self._filter_re(query, "id", _id)
        self._filter_re(query, "dns_indicator", dns_indicator)
        self._filter_re(query, "ip_address", ip_address)
        self._filter_re(query, "fqdn", fqdn)
        result = await self._search(
            query=query,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return ModelV2InstanceGetMulti(**result)

    async def update(
        self,
        _id: str,
        payload: ModelV2instancePut,
        fields: list,
    ) -> ModelV2InstanceGet:
        query = {"id": _id}
        data = payload.model_dump()
        result = await self._update(query=query, fields=fields, payload=data)
        return ModelV2InstanceGet(**result)


    async def update_ipa_otp(
        self,
        _id: str,
        ipa_otp: str,
        fields: list,
    ) -> ModelV2InstanceGet:
        query = {"id": _id}
        data = {"ipa_otp": ipa_otp}

        result = await self._update(query=query, fields=fields, payload=data)
        return ModelV2InstanceGet(**result)
