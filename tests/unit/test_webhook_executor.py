import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
import httpx
from catweazle.controller.webhook_executor import WebhookExecutor
from catweazle.model.v2.webhooks import ModelV2WebhookGet

class TestWebhookExecutor(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_log = MagicMock()
        self.mock_crud_webhooks = MagicMock()
        self.mock_crud_secrets = MagicMock()
        self.mock_crud_webhook_logs = MagicMock()
        self.mock_http_client = MagicMock(spec=httpx.AsyncClient)
        
        mock_response = httpx.Response(
            status_code=200,
            json={"status": "ok"},
            request=httpx.Request(
                method="POST",
                url="http://localhost",
            ),
        )
        self.mock_http_client.request = AsyncMock(
            return_value=mock_response,
        )

        self.executor = WebhookExecutor(
            log=self.mock_log,
            crud_webhooks=self.mock_crud_webhooks,
            crud_secrets=self.mock_crud_secrets,
            crud_webhook_logs=self.mock_crud_webhook_logs,
            http_client=self.mock_http_client,
        )

    async def test_resolve_placeholders_and_execute(self):
        webhook = ModelV2WebhookGet(
            id="test-webhook-1",
            url="http://localhost/webhook/{instance:id}",
            method="POST",
            triggers=["post-create"],
            headers={
                "X-Trigger-Type": "{trigger}",
            },
            query_params={
                "role": "{instance:meta:role}",
            },
            payload={
                "ip": "{instance:ip_address}",
            },
        )

        instance_data = {
            "id": "inst-1",
            "ip_address": "10.0.0.1",
            "dns_indicator": "test-num",
            "fqdn": "test-1.example.com",
            "meta": {
                "role": "web-server",
            },
        }

        self.mock_crud_webhook_logs.create = AsyncMock()

        await self.executor._execute_one(
            webhook=webhook,
            trigger="post-create",
            instance_data=instance_data,
        )

        self.mock_http_client.request.assert_called_once()
        kwargs = self.mock_http_client.request.call_args.kwargs

        self.assertEqual(
            first=kwargs["url"],
            second="http://localhost/webhook/inst-1",
        )
        self.assertEqual(
            first=kwargs["headers"].get("X-Trigger-Type"),
            second="post-create",
        )
        self.assertEqual(
            first=kwargs["params"].get("role"),
            second="web-server",
        )
        self.assertEqual(
            first=kwargs["json"].get("ip"),
            second="10.0.0.1",
        )
