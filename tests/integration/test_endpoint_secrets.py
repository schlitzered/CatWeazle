from datetime import datetime
from unittest.mock import AsyncMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.secrets import ModelV2SecretGet
from tests.base import EndpointTestCase

class TestEndpointSecrets(EndpointTestCase):
    async def test_create_secret_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )

        mock_secret = ModelV2SecretGet(
            id="aws_key",
            created=datetime.now(),
        )
        self.mock_crud_secrets.create = AsyncMock(
            return_value=mock_secret,
        )

        response = self.client.post(
            url="/api/v2/secrets",
            json={
                "id": "aws_key",
                "secret": "my_secret_val",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="aws_key",
        )

    async def test_delete_secret_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_permission = AsyncMock(
            return_value=user,
        )
        self.mock_crud_secrets.delete = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/secrets/aws_key",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
