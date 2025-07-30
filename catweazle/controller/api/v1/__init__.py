import logging

from fastapi import APIRouter

from catweazle.authorize import Authorize

from catweazle.controller.api.v1.instances import ControllerApiV1Instances

from catweazle.crud.instances import CrudInstances


class ControllerApiV1:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_instances: CrudInstances,
    ):
        self._router = APIRouter()
        self._log = log

        self.router.include_router(
            ControllerApiV1Instances(
                log=log,
                authorize=authorize,
                crud_instances=crud_instances,
            ).router,
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router
