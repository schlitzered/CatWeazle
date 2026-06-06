import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from catweazle.controller.api.v2 import ControllerApiV2

class EndpointTestCase(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_log = MagicMock()
        self.mock_authorize = MagicMock()
        self.mock_crud_ldap = MagicMock()
        self.mock_crud_foreman = []
        self.mock_crud_instances = MagicMock()
        self.mock_crud_permissions = MagicMock()
        self.mock_crud_secrets = MagicMock()
        self.mock_crud_users = MagicMock()
        self.mock_crud_credentials = MagicMock()
        self.mock_crud_webhook_logs = MagicMock()
        self.mock_crud_webhooks = MagicMock()
        self.mock_http = MagicMock()

        self.mock_crud_permissions.search = AsyncMock(
            return_value=MagicMock(result=[]),
        )
        self.mock_crud_permissions.delete_user_from_permissions = AsyncMock()
        self.mock_crud_credentials.delete_all_from_owner = AsyncMock()

        self.controller = ControllerApiV2(
            log=self.mock_log,
            authorize=self.mock_authorize,
            crud_ldap=self.mock_crud_ldap,
            crud_foreman_backends=self.mock_crud_foreman,
            crud_instances=self.mock_crud_instances,
            crud_permissions=self.mock_crud_permissions,
            crud_secrets=self.mock_crud_secrets,
            crud_users=self.mock_crud_users,
            crud_users_credentials=self.mock_crud_credentials,
            crud_webhook_logs=self.mock_crud_webhook_logs,
            crud_webhooks=self.mock_crud_webhooks,
            http=self.mock_http,
            bypass_ip_check=True,
        )

        self.app = FastAPI()
        self.app.add_middleware(
            middleware_class=SessionMiddleware,
            secret_key="test_key",
        )
        self.app.include_router(
            router=self.controller.router,
            prefix="/api/v2",
        )
        self.client = TestClient(
            app=self.app,
        )
