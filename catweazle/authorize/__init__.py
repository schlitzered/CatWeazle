import logging
import typing

from fastapi import Request

from catweazle.crud.users import CrudUsers
from catweazle.crud.credentials import CrudCredentials
from catweazle.crud.permissions import CrudPermissions

from catweazle.errors import AdminError
from catweazle.errors import CredentialError
from catweazle.errors import PermError
from catweazle.errors import ResourceNotFound
from catweazle.errors import SessionCredentialError

from catweazle.model.v2.users import ModelV2UserGet


class Authorize:
    def __init__(
        self,
        log: logging.Logger,
        crud_permissions: CrudPermissions,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
    ):
        self._crud_permission = crud_permissions
        self._crud_users = crud_users
        self._crud_users_credentials = crud_users_credentials
        self._log = log

    @property
    def crud_permission(self) -> CrudPermissions:
        return self._crud_permission

    @property
    def crud_users(self) -> CrudUsers:
        return self._crud_users

    @property
    def crud_users_credentials(self):
        return self._crud_users_credentials

    @property
    def log(self):
        return self._log

    async def get_user(self, request: Request) -> ModelV2UserGet:
        user = self.get_user_from_session(request=request)
        if not user:
            user = await self.get_user_from_credentials(request=request)
        if not user:
            raise SessionCredentialError
        user = await self.crud_users.get(_id=user, fields=["id", "admin"])
        return user

    async def get_user_from_credentials(
        self, request: Request
    ) -> ModelV2UserGet | None:
        try:
            self.log.info("trying to get user from credentials")
            user = await self.crud_users_credentials.check_credential(request=request)
            self.log.debug(f"received user {user} from credentials")
            return user
        except (CredentialError, ResourceNotFound):
            self.log.debug("trying to get user from credentials, failed")
            return None

    def get_user_from_session(self, request: Request) -> typing.Optional[str]:
        self.log.debug("trying to get user from session")
        user = request.session.get("username", None)
        if user is None:
            self.log.debug("trying to get user from session, failed")
            return None
        else:
            self.log.debug(f"received user {user} from session")
            return user

    async def require_admin(self, request, user=None) -> ModelV2UserGet:
        if not user:
            user = await self.get_user(request=request)
        if not user.admin:
            raise AdminError
        return user

    async def require_user(self, request) -> ModelV2UserGet:
        user = await self.get_user(request)
        return user

    async def require_permission(
        self, request, permission, user=None
    ) -> ModelV2UserGet:
        if not user:
            user = await self.get_user(request)
        try:
            return await self.require_admin(request=request, user=user)
        except AdminError:
            pass
        permissions = await self.crud_permission.search(
            users=f"^{user.id}$",
            permissions=f"^{permission}$",
            sort="id",
            sort_order="ascending",
            page=0,
            limit=1,
            fields=["id"],
        )
        if not permissions.result:
            raise PermError(permission=permission)
        return user
