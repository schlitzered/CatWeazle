import logging
from typing import List

import httpx
from fastapi import APIRouter

from catweazle.authorize import Authorize

from catweazle.controller.api import ControllerApi
from catweazle.controller.oauth import ControllerOauth

from catweazle.crud.credentials import CrudCredentials
from catweazle.crud.ldap import CrudLdap
from catweazle.crud.foreman import CrudForeman
from catweazle.crud.instances import CrudInstances
from catweazle.crud.oauth import CrudOAuth
from catweazle.crud.permissions import CrudPermissions
from catweazle.crud.secrets import CrudSecrets
from catweazle.crud.users import CrudUsers
from catweazle.crud.webhook_logs import CrudWebhookLogs
from catweazle.crud.webhooks import CrudWebhooks


class Controller:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_ldap: CrudLdap,
        crud_foreman_backends: List[CrudForeman],
        crud_instances: CrudInstances,
        crud_oauth: dict[str, CrudOAuth],
        crud_permissions: CrudPermissions,
        crud_secrets: CrudSecrets,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
        crud_webhook_logs: CrudWebhookLogs,
        crud_webhooks: CrudWebhooks,
        http: httpx.AsyncClient,
        bypass_ip_check: bool = False,
    ):
        self._log = log
        self._router = APIRouter()

        self.router.include_router(
            ControllerApi(
                log=log,
                authorize=authorize,
                crud_ldap=crud_ldap,
                crud_instances=crud_instances,
                crud_permissions=crud_permissions,
                crud_secrets=crud_secrets,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
                crud_webhook_logs=crud_webhook_logs,
                crud_webhooks=crud_webhooks,
                crud_foreman_backends=crud_foreman_backends,
                http=http,
                bypass_ip_check=bypass_ip_check,
            ).router,
            prefix="/api",
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerOauth(
                log=log,
                curd_oauth=crud_oauth,
                crud_users=crud_users,
                http=http,
            ).router,
            prefix="/oauth",
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router

    @property
    def log(self):
        return self._log
