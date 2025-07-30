import logging

import httpx
from fastapi import APIRouter

from catweazle.controller.oauth.authenticate import ControllerOauthAuthenticate
from catweazle.crud.oauth import CrudOAuth
from catweazle.crud.users import CrudUsers


class ControllerOauth:
    def __init__(
        self,
        log: logging.Logger,
        curd_oauth: dict[str, CrudOAuth],
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
    ):
        self._log = log
        self._router = APIRouter()

        self.router.include_router(
            ControllerOauthAuthenticate(
                log=log,
                crud_oauth=curd_oauth,
                crud_users=crud_users,
                http=http,
            ).router,
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router
