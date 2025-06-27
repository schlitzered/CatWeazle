import logging
from typing import List

import httpx
from fastapi import APIRouter

from catweazle.authorize import Authorize

from catweazle.controller.api.v2 import ControllerApiV2

from catweazle.crud.credentials import CrudCredentials
from catweazle.crud.ldap import CrudLdap
from catweazle.crud.foreman import CrudForeman
from catweazle.crud.instances import CrudInstances
from catweazle.crud.permissions import CrudPermissions
from catweazle.crud.users import CrudUsers


class ControllerApi:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_ldap: CrudLdap,
        crud_foreman_backends: List[CrudForeman],
        crud_instances: CrudInstances,
        crud_permissions: CrudPermissions,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
        http: httpx.AsyncClient,
    ):
        self._router = APIRouter()
        self._log = log

        self.router.include_router(
            ControllerApiV2(
                log=log,
                authorize=authorize,
                crud_ldap=crud_ldap,
                crud_foreman_backends=crud_foreman_backends,
                crud_instances=crud_instances,
                crud_permissions=crud_permissions,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
                http=http,
            ).router,
            prefix="/v2",
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router

    @property
    def log(self):
        return self._log
