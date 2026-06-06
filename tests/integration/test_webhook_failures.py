from unittest.mock import AsyncMock
from unittest.mock import MagicMock
import httpx
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.instances import ModelV2InstanceGet
from catweazle.model.v2.webhooks import ModelV2WebhookGet
from tests.base import EndpointTestCase

class TestWebhookFailures(EndpointTestCase):
    async def test_create_instance_pre_webhook_fail(self):
        user = ModelV2UserGet(
            id="test_user",
            admin=False,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        webhook = ModelV2WebhookGet(
            id="webhook-fail-1",
            url="http://localhost:8888/fail",
            method="POST",
            triggers=["pre-create"],
            fail_on_error=True,
        )
        def mock_search(*args, **kwargs):
            query = kwargs.get("query")
            if query and query.get("triggers") == "pre-create":
                return MagicMock(result=[webhook])
            return MagicMock(result=[])

        self.mock_crud_webhooks.search = AsyncMock(
            side_effect=mock_search,
        )

        mock_instance = ModelV2InstanceGet(
            id="inst1",
            dns_indicator="web-NUM",
            ip_address="192.168.1.10",
            fqdn="web-1.example.com",
        )
        self.mock_crud_instances.create = AsyncMock(
            return_value=mock_instance,
        )
        self.mock_crud_instances.get = AsyncMock(
            return_value=mock_instance,
        )
        self.mock_crud_instances.delete = AsyncMock(
            return_value={},
        )

        self.mock_crud_webhook_logs.create = AsyncMock()
        mock_response = httpx.Response(
            status_code=400,
            json={"error": "bad request"},
            request=httpx.Request(
                method="POST",
                url="http://localhost:8888/fail",
            ),
        )
        self.mock_http.request = AsyncMock(
            return_value=mock_response,
        )

        response = self.client.post(
            url="/api/v2/instances/inst1",
            json={
                "dns_indicator": "web-NUM",
                "ip_address": "192.168.1.10",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=400,
        )
        self.assertEqual(
            first=response.json().get("detail"),
            second="Webhook webhook-fail-1 execution failed",
        )

        self.mock_crud_instances.delete.assert_called_once_with(
            _id="inst1",
        )
