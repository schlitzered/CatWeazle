import logging
from typing import List

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize
from catweazle.crud.webhooks import CrudWebhooks
from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.webhooks import ModelV2WebhookGet
from catweazle.model.v2.webhooks import ModelV2WebhookGetMulti
from catweazle.model.v2.webhooks import ModelV2WebhookPost
from catweazle.model.v2.webhooks import ModelV2WebhookPut


class ControllerApiV2Webhooks:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_webhooks: CrudWebhooks,
    ):
        self._authorize = authorize
        self._crud_webhooks = crud_webhooks
        self._log = log
        self._router = APIRouter(
            prefix="/webhooks",
            tags=["webhooks"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=ModelV2WebhookGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "",
            self.create,
            response_model=ModelV2WebhookGet,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "/{webhook_id}",
            self.delete,
            response_model=ModelV2DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{webhook_id}",
            self.get,
            response_model=ModelV2WebhookGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{webhook_id}",
            self.update,
            response_model=ModelV2WebhookGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_webhooks(self):
        return self._crud_webhooks

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def create(
        self,
        request: Request,
        payload: ModelV2WebhookPost,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2WebhookGet:
        await self.authorize.check_session(request=request, admin=True)
        return await self.crud_webhooks.create(payload=payload, fields=fields)

    async def delete(self, request: Request, webhook_id: str) -> ModelV2DataDelete:
        await self.authorize.check_session(request=request, admin=True)
        return await self.crud_webhooks.delete(_id=webhook_id)

    async def get(
        self,
        request: Request,
        webhook_id: str,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2WebhookGet:
        await self.authorize.check_session(request=request, admin=True)
        return await self.crud_webhooks.get(_id=webhook_id, fields=fields)

    async def search(
        self,
        request: Request,
        webhook_id: str = Query(None, alias="id"),
        fields: List[str] = Query(None, alias="field"),
        sort: str = Query(None),
        sort_order: sort_order_literal = Query(None, alias="sort-order"),
        page: int = Query(None),
        limit: int = Query(None),
    ) -> ModelV2WebhookGetMulti:
        await self.authorize.check_session(request=request, admin=True)
        return await self.crud_webhooks.search(
            _id=webhook_id,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )

    async def update(
        self,
        request: Request,
        webhook_id: str,
        payload: ModelV2WebhookPut,
        fields: List[str] = Query(None, alias="field"),
    ) -> ModelV2WebhookGet:
        await self.authorize.check_session(request=request, admin=True)
        return await self.crud_webhooks.update(
            _id=webhook_id, payload=payload, fields=fields
        )
