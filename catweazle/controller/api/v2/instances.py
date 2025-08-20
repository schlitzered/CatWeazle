import logging
from typing import List
from typing import Set

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize

from catweazle.errors import SessionCredentialError

from catweazle.crud.instances import CrudInstances
from catweazle.crud.foreman import CrudForeman
from catweazle.errors import BackendError

from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.instances import filter_list
from catweazle.model.v2.instances import filter_literal
from catweazle.model.v2.instances import sort_literal
from catweazle.model.v2.instances import ModelV2InstanceGet
from catweazle.model.v2.instances import ModelV2InstanceGetMulti
from catweazle.model.v2.instances import ModelV2instancePost
from catweazle.model.v2.instances import ModelV2instancePut


class ControllerApiV2Instances:

    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_instances: CrudInstances,
        crud_foreman_backends: List[CrudForeman],
    ):
        self._authorize = authorize
        self._crud_instances = crud_instances
        self._crud_foreman_backends = crud_foreman_backends
        self._log = log
        self._router = APIRouter(
            prefix="/instances",
            tags=["instances"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=ModelV2InstanceGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{instance_id}",
            self.create,
            response_model=ModelV2InstanceGet,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "/{instance_id}",
            self.delete,
            response_model=ModelV2DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{instance_id}",
            self.get,
            response_model=ModelV2InstanceGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{instance_id}",
            self.update,
            response_model=ModelV2InstanceGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_instances(self):
        return self._crud_instances

    @property
    def crud_foreman_backends(self):
        return self._crud_foreman_backends

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def create(
        self,
        data: ModelV2instancePost,
        instance_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_permission(
            request=request, permission="INSTANCE:POST"
        )

        instance = await self.crud_instances.create(
            _id=instance_id, payload=data, fields=list(fields)
        )
        for foreman in self.crud_foreman_backends:
            try:
                await foreman.create_dns(
                    fqdn=instance.fqdn,
                    ip_address=instance.ip_address,
                )
                await foreman.create_realm(
                    fqdn=instance.fqdn,
                )
            except BackendError as err:
                self.log.error(
                    f"Failed to create DNS or realm for instance {instance_id} in foreman backend {foreman.name}"
                )
                await self.delete(
                    instance_id=instance_id,
                    request=request,
                )
                raise err
        return instance

    async def delete(self, request: Request, instance_id: str):
        await self.authorize.require_permission(
            request=request, permission="INSTANCE:DELETE"
        )
        instance = await self.crud_instances.get(
            _id=instance_id, fields=["fqdn", "ip_address"]
        )
        for foreman in self.crud_foreman_backends:
            try:
                await foreman.delete_dns(
                    fqdn=instance.fqdn,
                    ip_address=instance.ip_address,
                )
            except BackendError:
                pass
            try:
                await foreman.delete_realm(
                    fqdn=instance.fqdn,
                )
            except BackendError:
                pass
        return await self.crud_instances.delete(_id=instance_id)

    async def get(
        self,
        instance_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        try:
            await self.authorize.require_user(request=request)
            fields.discard("ipa_otp")
        except SessionCredentialError as err:
            result = await self.crud_instances.get(
                _id=instance_id, fields=["id", "ip_address"]
            )
            if result.ip_address != request.client.host:
                raise err

        return await self.crud_instances.get(_id=instance_id, fields=list(fields))

    async def search(
        self,
        request: Request,
        instance_id: str = Query(
            description="filter: regular_expressions", default=None
        ),
        dns_indicator: str = Query(
            description="filter: regular_expressions", default=None
        ),
        ip_address: str = Query(
            description="filter: regular_expressions", default=None
        ),
        fqdn: str = Query(description="filter: regular_expressions", default=None),
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
        await self.authorize.require_user(request=request)
        fields.discard("ipa_otp")
        return await self.crud_instances.search(
            _id=instance_id,
            dns_indicator=dns_indicator,
            ip_address=ip_address,
            fqdn=fqdn,
            fields=list(fields),
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )

    async def update(
        self,
        data: ModelV2instancePut,
        instance_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_permission(
            request=request, permission="INSTANCE:POST"
        )
        return await self.crud_instances.update(
            _id=instance_id, payload=data, fields=list(fields)
        )
