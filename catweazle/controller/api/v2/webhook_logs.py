import logging
from typing import Optional

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from catweazle.authorize import Authorize

from catweazle.crud.webhook_logs import CrudWebhookLogs

from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.webhook_logs import ModelV2WebhookLogGetMulti


class ControllerApiV2WebhookLogs:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_webhook_logs: CrudWebhookLogs,
    ):
        self._authorize = authorize
        self._crud_webhook_logs = crud_webhook_logs
        self._log = log
        self._router = APIRouter(
            prefix="/webhook-logs",
            tags=["webhook-logs"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=ModelV2WebhookLogGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_webhook_logs(self):
        return self._crud_webhook_logs

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def search(
        self,
        request: Request,
        instance_id: Optional[str] = Query(
            description="filter: regular_expression",
            default=None,
        ),
        webhook_id: Optional[str] = Query(
            description="filter: regular_expression",
            default=None,
        ),
        trigger: Optional[str] = Query(
            description="filter: regular_expression",
            default=None,
        ),
        sort: str = Query(default="created_at"),
        sort_order: sort_order_literal = Query(default="descending"),
        page: int = Query(
            default=0,
            ge=0,
            description="pagination index",
        ),
        limit: int = Query(
            default=10,
            ge=10,
            le=1000,
            description="pagination limit, min value 10, max value 1000",
        ),
    ) -> ModelV2WebhookLogGetMulti:
        await self.authorize.require_permission(
            request=request,
            permission="WEBHOOK_LOG:GET",
        )
        return await self.crud_webhook_logs.search(
            instance_id=instance_id,
            webhook_id=webhook_id,
            trigger=trigger,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
