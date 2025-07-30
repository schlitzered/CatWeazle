import logging
from typing import Set

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize
from catweazle.errors import SessionCredentialError

from catweazle.crud.instances import CrudInstances

from catweazle.model.v2.instances import filter_list
from catweazle.model.v2.instances import filter_literal
from catweazle.model.v1.instances import ModelV1InstanceGet


class ControllerApiV1Instances:

    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_instances: CrudInstances,
    ):
        self._authorize = authorize
        self._crud_instances = crud_instances
        self._log = log
        self._router = APIRouter(
            prefix="/instances",
            tags=["instances"],
        )
        self.router.add_api_route(
            "/{instance_id}",
            self.get,
            response_model=ModelV1InstanceGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_instances(self):
        return self._crud_instances

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

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

        result = await self.crud_instances.get(_id=instance_id, fields=list(fields))
        return ModelV1InstanceGet(data=result)
