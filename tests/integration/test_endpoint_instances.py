from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.instances import ModelV2InstanceGet
from tests.base import EndpointTestCase

class TestEndpointInstances(EndpointTestCase):
    async def test_create_instance_success(self):
        user = ModelV2UserGet(
            id="test_user",
            admin=False,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )
        self.mock_crud_webhooks.search = AsyncMock(
            return_value=MagicMock(result=[]),
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

        response = self.client.post(
            url="/api/v2/instances/inst1",
            json={
                "dns_indicator": "web-NUM",
                "ip_address": "192.168.1.10",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="inst1",
        )

    async def test_delete_instance_success(self):
        user = ModelV2UserGet(
            id="test_user",
            admin=False,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )
        self.mock_crud_webhooks.search = AsyncMock(
            return_value=MagicMock(result=[]),
        )

        mock_instance = ModelV2InstanceGet(
            id="inst1",
            dns_indicator="web-NUM",
            ip_address="192.168.1.10",
            fqdn="web-1.example.com",
        )
        self.mock_crud_instances.get = AsyncMock(
            return_value=mock_instance,
        )
        self.mock_crud_instances.delete = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/instances/inst1",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
