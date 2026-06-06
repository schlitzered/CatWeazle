from datetime import datetime
from unittest.mock import AsyncMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.common import ModelV2MetaMulti
from catweazle.model.v2.webhook_logs import ModelV2WebhookLogGetMulti
from catweazle.model.v2.webhook_logs import ModelV2WebhookLogGet
from tests.base import EndpointTestCase

class TestEndpointWebhookLogs(EndpointTestCase):
    async def test_search_webhook_logs_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        mock_logs = ModelV2WebhookLogGetMulti(
            result=[
                ModelV2WebhookLogGet(
                    instance_id="inst1",
                    webhook_id="wh1",
                    trigger="post-create",
                    url="http://localhost",
                    method="POST",
                    created_at=datetime.now(),
                ),
            ],
            meta=ModelV2MetaMulti(
                result_size=1,
            ),
        )
        self.mock_crud_webhook_logs.search = AsyncMock(
            return_value=mock_logs,
        )

        response = self.client.get(
            url="/api/v2/webhook-logs",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
        self.assertEqual(
            first=len(response.json().get("result")),
            second=1,
        )
