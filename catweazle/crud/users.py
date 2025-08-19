import logging
import typing

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from passlib.hash import pbkdf2_sha512
import pymongo
import pymongo.errors

from catweazle.crud.common import CrudMongo
from catweazle.crud.ldap import CrudLdap

from catweazle.errors import AuthenticationError
from catweazle.errors import BackendError

from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.authenticate import ModelV2AuthenticatePost
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.users import ModelV2UserGetMulti
from catweazle.model.v2.users import ModelV2UserPost
from catweazle.model.v2.users import ModelV2UserPut


class CrudUsers(CrudMongo):
    def __init__(
        self,
        log: logging.Logger,
        coll: AsyncIOMotorCollection,
        crud_ldap: CrudLdap,
    ):
        super(CrudUsers, self).__init__(log=log, coll=coll)
        self._crud_ldap = crud_ldap

    async def index_create(self) -> None:
        self.log.info(f"creating {self.resource_type} indices")
        await self.coll.create_index([("id", pymongo.ASCENDING)], unique=True)
        self.log.info(f"creating {self.resource_type} indices, done")

    @property
    def crud_ldap(self):
        return self._crud_ldap

    @staticmethod
    def _password(password) -> str:
        return pbkdf2_sha512.encrypt(password, rounds=100000, salt_size=32)

    async def check_credentials(self, credentials: ModelV2AuthenticatePost) -> str:
        user = credentials.user
        password = credentials.password
        try:
            result = await self._coll.find_one(
                filter={"id": user},
                projection={"password": 1, "backend": 1},
            )
            if not result:
                await self.check_credentials_ldap_and_create_user(
                    credentials=credentials
                )
            elif result["backend"] == "internal":
                if not pbkdf2_sha512.verify(password, result["password"]):
                    raise AuthenticationError
            elif result["backend"] == "ldap":
                try:
                    await self.crud_ldap.check_user_credentials(
                        user=user, password=password
                    )
                except AuthenticationError:
                    raise AuthenticationError
            else:
                self.log.error(
                    f"auth backend mismatch, expected ldap or internal, got: {result['backend']}"
                )
                raise AuthenticationError(
                    msg="backend mismatch, please contact the administrator"
                )
            return user
        except pymongo.errors.ConnectionFailure as err:
            self.log.error(f"backend error: {err}")
            raise BackendError()

    async def check_credentials_ldap_and_create_user(
        self, credentials: ModelV2AuthenticatePost
    ):
        ldap_user = await self.crud_ldap.check_user_credentials(
            user=credentials.user,
            password=credentials.password,
        )
        result = await self.create_external(
            _id=credentials.user,
            payload=ModelV2UserPut(
                name=f"{ldap_user['givenName'][0]} {ldap_user['sn'][0]}",
                email=ldap_user["mail"][0],
                admin=False,
            ),
            backend="ldap",
            fields=["_id"],
        )
        return result

    async def create(
        self,
        _id: str,
        payload: ModelV2UserPost,
        fields: list,
    ) -> ModelV2UserGet:
        data = payload.model_dump()
        data["id"] = _id
        data["password"] = self._password(payload.password)
        data["backend"] = "internal"
        result = await self._create(payload=data, fields=fields)
        return ModelV2UserGet(**result)

    async def create_external(
        self,
        _id: str,
        payload: ModelV2UserPut,
        fields: list,
        backend: str,
    ) -> ModelV2UserGet:
        data = payload.model_dump()
        data["id"] = _id
        data["backend"] = backend
        result = await self._create(payload=data, fields=fields)
        return ModelV2UserGet(**result)

    async def delete(
        self,
        _id: str,
    ) -> ModelV2DataDelete:
        query = {"id": _id}
        await self._delete(query=query)
        return ModelV2DataDelete()

    async def get(
        self,
        _id: str,
        fields: list,
    ) -> ModelV2UserGet:
        query = {"id": _id}
        result = await self._get(query=query, fields=fields)
        return ModelV2UserGet(**result)

    async def resource_exists(
        self,
        _id: str,
    ) -> ObjectId:
        query = {"id": _id}
        return await self._resource_exists(query=query)

    async def search(
        self,
        _id: typing.Optional[str] = None,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
    ) -> ModelV2UserGetMulti:
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
        return ModelV2UserGetMulti(**result)

    async def update(
        self,
        _id: str,
        payload: ModelV2UserPut,
        fields: list,
    ) -> ModelV2UserGet:
        query = {"id": _id}
        data = payload.model_dump()
        if data["password"] is not None:
            user_orig = await self.get(_id=_id, fields=["backend"])
            if user_orig.backend == "internal":
                data["password"] = self._password(data["password"])
            else:
                data["passwort"] = None

        result = await self._update(query=query, fields=fields, payload=data)
        return ModelV2UserGet(**result)
