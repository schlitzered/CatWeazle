import logging


from fastapi import APIRouter
from fastapi import Request

import httpx

from catweazle.authorize import Authorize
from catweazle.crud.users import CrudUsers

from catweazle.errors import AuthenticationError

from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.authenticate import ModelV2AuthenticateGetUser
from catweazle.model.v2.authenticate import ModelV2AuthenticatePost


class ControllerApiV2Authenticate:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
    ):
        self._authorize = authorize
        self._crud_users = crud_users
        self._http = http
        self._log = log
        self._router = APIRouter(
            prefix="/authenticate",
            tags=["authenticate"],
        )

        self.router.add_api_route(
            "", self.get, response_model=ModelV2AuthenticateGetUser, methods=["GET"]
        )
        self.router.add_api_route(
            "",
            self.create,
            response_model=ModelV2AuthenticateGetUser,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "", self.delete, response_model=ModelV2DataDelete, methods=["DELETE"]
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_users(self):
        return self._crud_users

    @property
    def http(self):
        return self._http

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def get(self, request: Request):
        user = await self.authorize.get_user(request=request)
        if not user:
            raise AuthenticationError
        return {"user": user.id}

    async def create(
        self,
        data: ModelV2AuthenticatePost,
        request: Request,
    ):
        user = await self.crud_users.check_credentials(credentials=data)
        request.session["username"] = user
        return {"user": user}

    @staticmethod
    async def delete(request: Request):
        request.session.clear()
        return {}
