import logging
from typing import List

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize
from catweazle.crud.secrets import CrudSecrets
from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.secrets import ModelV2SecretGet
from catweazle.model.v2.secrets import ModelV2SecretGetMulti
from catweazle.model.v2.secrets import ModelV2SecretPost
from catweazle.model.v2.secrets import ModelV2SecretPut


class ControllerApiV2Secrets:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_secrets: CrudSecrets,
    ):
        self._authorize = authorize
        self._crud_secrets = crud_secrets
        self._log = log
        self._router = APIRouter(
            prefix="/secrets",
            tags=["secrets"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=ModelV2SecretGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "",
            self.create,
            response_model=ModelV2SecretGet,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "/{secret_id}",
            self.delete,
            response_model=ModelV2DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{secret_id}",
            self.get,
            response_model=ModelV2SecretGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{secret_id}",
            self.update,
            response_model=ModelV2SecretGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_secrets(self):
        return self._crud_secrets

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def create(
        self,
        request: Request,
        payload: ModelV2SecretPost,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2SecretGet:
        await self.authorize.require_permission(
            request=request,
            permission="SECRET:POST",
        )
        return await self.crud_secrets.create(
            payload=payload,
            fields=fields,
        )

    async def delete(self, request: Request, secret_id: str) -> ModelV2DataDelete:
        await self.authorize.require_permission(
            request=request,
            permission="SECRET:DELETE",
        )
        return await self.crud_secrets.delete(_id=secret_id)

    async def get(
        self,
        request: Request,
        secret_id: str,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2SecretGet:
        await self.authorize.require_user(request=request)
        return await self.crud_secrets.get(
            _id=secret_id,
            fields=fields,
        )

    async def search(
        self,
        request: Request,
        secret_id: str = Query(None, alias="id"),
        fields: List[str] = Query(None, alias="field"),
        sort: str = Query(None),
        sort_order: sort_order_literal = Query(None, alias="sort-order"),
        page: int = Query(None),
        limit: int = Query(None),
    ) -> ModelV2SecretGetMulti:
        await self.authorize.require_user(request=request)
        return await self.crud_secrets.search(
            _id=secret_id,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )

    async def update(
        self,
        request: Request,
        secret_id: str,
        payload: ModelV2SecretPut,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2SecretGet:
        await self.authorize.require_permission(
            request=request,
            permission="SECRET:POST",
        )
        return await self.crud_secrets.update(
            _id=secret_id,
            payload=payload,
            fields=fields,
        )
