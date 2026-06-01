import logging
from typing import List

import httpx
from fastapi import APIRouter

from catweazle.authorize import Authorize

from catweazle.controller.api.v2.authenticate import ControllerApiV2Authenticate
from catweazle.controller.api.v2.instances import ControllerApiV2Instances
from catweazle.controller.api.v2.permissions import ControllerApiV2Permissions
from catweazle.controller.api.v2.secrets import ControllerApiV2Secrets
from catweazle.controller.api.v2.users import ControllerApiV2Users
from catweazle.controller.api.v2.users_credentials import (
    ControllerApiV2UsersCredentials,
)
from catweazle.controller.api.v2.webhooks import ControllerApiV2Webhooks
from catweazle.controller.api.v2.webhook_logs import ControllerApiV2WebhookLogs

from catweazle.crud.credentials import CrudCredentials
from catweazle.crud.ldap import CrudLdap
from catweazle.crud.foreman import CrudForeman
from catweazle.crud.instances import CrudInstances
from catweazle.crud.permissions import CrudPermissions
from catweazle.crud.secrets import CrudSecrets
from catweazle.crud.users import CrudUsers
from catweazle.crud.webhook_logs import CrudWebhookLogs
from catweazle.crud.webhooks import CrudWebhooks


class ControllerApiV2:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_ldap: CrudLdap,
        crud_foreman_backends: List[CrudForeman],
        crud_instances: CrudInstances,
        crud_permissions: CrudPermissions,
        crud_secrets: CrudSecrets,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
        crud_webhook_logs: CrudWebhookLogs,
        crud_webhooks: CrudWebhooks,
        http: httpx.AsyncClient,
        bypass_ip_check: bool = False,
    ):
        self._router = APIRouter()
        self._log = log

        self.router.include_router(
            ControllerApiV2Authenticate(
                log=log,
                authorize=authorize,
                crud_users=crud_users,
                http=http,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2Instances(
                log=log,
                authorize=authorize,
                crud_instances=crud_instances,
                crud_foreman_backends=crud_foreman_backends,
                crud_secrets=crud_secrets,
                crud_webhooks=crud_webhooks,
                http_client=http,
                bypass_ip_check=bypass_ip_check,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2Permissions(
                log=log,
                authorize=authorize,
                crud_permissions=crud_permissions,
                crud_ldap=crud_ldap,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2Secrets(
                log=log,
                authorize=authorize,
                crud_secrets=crud_secrets,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2Users(
                log=log,
                authorize=authorize,
                crud_permissions=crud_permissions,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2UsersCredentials(
                log=log,
                authorize=authorize,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2Webhooks(
                log=log,
                authorize=authorize,
                crud_webhooks=crud_webhooks,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ControllerApiV2WebhookLogs(
                log=log,
                authorize=authorize,
                crud_webhook_logs=crud_webhook_logs,
            ).router,
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router
