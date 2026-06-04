import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
import ssl
import httpx
from catweazle.controller.webhook_executor import WebhookExecutor
from catweazle.errors import WebhookExecutionError
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

        self.mock_crud_webhook_logs.create.assert_called_once()
        log_kwargs = self.mock_crud_webhook_logs.create.call_args.kwargs
        self.assertEqual(
            first=log_kwargs["response_status_code"],
            second=200,
        )

    async def test_webhook_http_error_logged(self):
        webhook = ModelV2WebhookGet(
            id="test-webhook-1",
            url="http://localhost/webhook",
            method="POST",
            triggers=["post-create"],
        )

        instance_data = {
            "id": "inst-1",
            "ip_address": "10.0.0.1",
            "dns_indicator": "test-num",
            "fqdn": "test-1.example.com",
        }

        self.mock_crud_webhook_logs.create = AsyncMock()
        mock_response = httpx.Response(
            status_code=500,
            json={
                "error": "internal error",
            },
            request=httpx.Request(
                method="POST",
                url="http://localhost",
            ),
        )
        self.mock_http_client.request = AsyncMock(
            return_value=mock_response,
        )

        with self.assertRaises(
            expected_exception=httpx.HTTPStatusError,
        ):
            await self.executor._execute_one(
                webhook=webhook,
                trigger="post-create",
                instance_data=instance_data,
            )

        self.mock_crud_webhook_logs.create.assert_called_once()
        log_kwargs = self.mock_crud_webhook_logs.create.call_args.kwargs
        self.assertEqual(
            first=log_kwargs["response_status_code"],
            second=500,
        )

    async def test_execute_pre_trigger_fail_on_error(self):
        webhook = ModelV2WebhookGet(
            id="test-webhook-1",
            url="http://localhost/webhook",
            method="POST",
            triggers=["pre-create"],
            fail_on_error=True,
        )

        instance_data = {
            "id": "inst-1",
            "ip_address": "10.0.0.1",
            "dns_indicator": "test-num",
            "fqdn": "test-1.example.com",
        }

        self.mock_crud_webhooks.search = AsyncMock(
            return_value=MagicMock(
                result=[webhook],
            ),
        )

        mock_response = httpx.Response(
            status_code=500,
            json={
                "error": "internal error",
            },
            request=httpx.Request(
                method="POST",
                url="http://localhost",
            ),
        )
        self.mock_http_client.request = AsyncMock(
            return_value=mock_response,
        )
        self.mock_crud_webhook_logs.create = AsyncMock()

        with self.assertRaises(
            expected_exception=WebhookExecutionError,
        ):
            await self.executor.execute(
                trigger="pre-create",
                instance_data=instance_data,
            )

    async def test_execute_one_with_ssl(self):
        webhook = ModelV2WebhookGet(
            id="test-webhook-ssl",
            url="https://localhost/webhook",
            method="GET",
            triggers=["post-create"],
            ssl_ca="---BEGIN CERTIFICATE---\nCA\n---END CERTIFICATE---",
            ssl_cert="---BEGIN CERTIFICATE---\nCERT\n---END CERTIFICATE---",
            ssl_key="encrypted-key",
        )

        instance_data = {
            "id": "inst-1",
        }

        self.mock_crud_webhooks.decrypt = MagicMock(
            return_value="decrypted-key",
        )
        self.mock_crud_webhook_logs.create = AsyncMock()

        with patch(
            target="ssl.create_default_context",
        ) as mock_create_ctx:
            mock_ssl_ctx = MagicMock()
            mock_create_ctx.return_value = mock_ssl_ctx
            with patch(
                target="httpx.AsyncClient",
            ) as mock_client_class:
                mock_client_instance = AsyncMock()
                mock_client_instance.request = AsyncMock(
                    return_value=httpx.Response(
                        status_code=200,
                        request=httpx.Request(
                            method="GET",
                            url="https://localhost",
                        ),
                    ),
                )
                mock_client_class.return_value = mock_client_instance
                mock_client_instance.__aenter__.return_value = mock_client_instance

                await self.executor._execute_one(
                    webhook=webhook,
                    trigger="post-create",
                    instance_data=instance_data,
                )

                mock_client_class.assert_called()
                call_kwargs = mock_client_class.call_args.kwargs
                self.assertEqual(
                    first=call_kwargs["verify"],
                    second=mock_ssl_ctx,
                )
                mock_ssl_ctx.load_verify_locations.assert_called_with(
                    cadata=webhook.ssl_ca,
                )
                mock_ssl_ctx.load_cert_chain.assert_called()

