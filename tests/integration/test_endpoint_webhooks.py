from unittest.mock import AsyncMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.webhooks import ModelV2WebhookGet
from tests.base import EndpointTestCase

class TestEndpointWebhooks(EndpointTestCase):
    async def test_create_webhook_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        mock_webhook = ModelV2WebhookGet(
            id="webhook1",
            url="http://localhost/webhook",
            method="POST",
            triggers=["post-create"],
        )
        self.mock_crud_webhooks.create = AsyncMock(
            return_value=mock_webhook,
        )

        response = self.client.post(
            url="/api/v2/webhooks",
            json={
                "id": "webhook1",
                "url": "http://localhost/webhook",
                "method": "POST",
                "triggers": ["post-create"],
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="webhook1",
        )

    async def test_delete_webhook_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )
        self.mock_crud_webhooks.delete = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/webhooks/webhook1",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )

    async def test_create_webhook_with_acceptable_status_codes_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        mock_webhook = ModelV2WebhookGet(
            id="webhook1",
            url="http://localhost/webhook",
            method="POST",
            triggers=["post-create"],
            acceptable_status_codes=["200", "201", "2xx"],
        )
        self.mock_crud_webhooks.create = AsyncMock(
            return_value=mock_webhook,
        )

        response = self.client.post(
            url="/api/v2/webhooks",
            json={
                "id": "webhook1",
                "url": "http://localhost/webhook",
                "method": "POST",
                "triggers": ["post-create"],
                "acceptable_status_codes": [
                    "200",
                    "201",
                    "2xx",
                ],
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json()["acceptable_status_codes"],
            second=["200", "201", "2xx"],
        )

    async def test_create_webhook_with_acceptable_status_codes_failure(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        response = self.client.post(
            url="/api/v2/webhooks",
            json={
                "id": "webhook1",
                "url": "http://localhost/webhook",
                "method": "POST",
                "triggers": ["post-create"],
                "acceptable_status_codes": "200 201 2xx",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=422,
        )

