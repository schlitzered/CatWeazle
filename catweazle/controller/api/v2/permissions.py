import logging
from typing import Set

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize

from catweazle.crud.permissions import CrudPermissions
from catweazle.crud.ldap import CrudLdap

from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.permissions import filter_list
from catweazle.model.v2.permissions import filter_literal
from catweazle.model.v2.permissions import sort_literal
from catweazle.model.v2.permissions import ModelV2PermissionGet
from catweazle.model.v2.permissions import ModelV2PermissionGetMulti
from catweazle.model.v2.permissions import ModelV2PermissionPost
from catweazle.model.v2.permissions import ModelV2PermissionPut


class ControllerApiV2Permissions:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_permissions: CrudPermissions,
        crud_ldap: CrudLdap,
    ):
        self._authorize = authorize
        self._crud_permissions = crud_permissions
        self._crud_ldap = crud_ldap
        self._log = log
        self._router = APIRouter(
            prefix="/permissions",
            tags=["permissions"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=ModelV2PermissionGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{permission_id}",
            self.create,
            response_model=ModelV2PermissionGet,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "/{permission_id}",
            self.delete,
            response_model=ModelV2DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{permission_id}",
            self.get,
            response_model=ModelV2PermissionGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{permission_id}",
            self.update,
            response_model=ModelV2PermissionGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_permissions(self):
        return self._crud_permissions

    @property
    def crud_ldap(self):
        return self._crud_ldap

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def create(
        self,
        request: Request,
        data: ModelV2PermissionPost,
        permission_id: str,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_admin(request=request)
        if data.ldap_group:
            data.users = await self.crud_ldap.get_logins_from_group(
                group=data.ldap_group
            )
        return await self.crud_permissions.create(
            _id=permission_id,
            payload=data,
            fields=list(fields),
        )

    async def delete(
        self,
        request: Request,
        permission_id: str,
    ):
        await self.authorize.require_admin(request=request)
        return await self.crud_permissions.delete(
            _id=permission_id,
        )

    async def get(
        self,
        permission_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_admin(request=request)
        return await self.crud_permissions.get(_id=permission_id, fields=list(fields))

    async def search(
        self,
        request: Request,
        permission_id: str = Query(
            description="filter: regular_expressions", default=None
        ),
        ldap_group: str = Query(
            description="filter: regular_expressions", default=None
        ),
        users: str = Query(description="filter: regular_expressions", default=None),
        fields: Set[filter_literal] = Query(default=filter_list),
        sort: sort_literal = Query(default="id"),
        sort_order: sort_order_literal = Query(default="ascending"),
        page: int = Query(default=0, ge=0, description="pagination index"),
        limit: int = Query(
            default=10,
            ge=10,
            le=1000,
            description="pagination limit, min value 10, max value 1000",
        ),
    ):
        await self.authorize.require_admin(request=request)
        return await self.crud_permissions.search(
            _id=permission_id,
            ldap_group=ldap_group,
            users=users,
            fields=list(fields),
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )

    async def update(
        self,
        data: ModelV2PermissionPut,
        permission_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_admin(request=request)
        current_group = await self.crud_permissions.get(
            _id=permission_id,
            fields=["ldap_group", "users"],
        )
        if data.ldap_group:
            data.users = await self.crud_ldap.get_logins_from_group(
                group=data.ldap_group
            )
        elif current_group.ldap_group:
            data.users = await self.crud_ldap.get_logins_from_group(
                group=current_group.ldap_group
            )
        return await self.crud_permissions.update(
            _id=permission_id,
            payload=data,
            fields=list(fields),
        )
