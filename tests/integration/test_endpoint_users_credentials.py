from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.credentials import ModelV2CredentialPostResult
from tests.base import EndpointTestCase

class TestEndpointUsersCredentials(EndpointTestCase):
    async def test_create_credential_self(self):
        user = ModelV2UserGet(
            id="test_user",
            admin=False,
        )
        self.mock_authorize.get_user = AsyncMock(
            return_value=user,
        )
        self.mock_crud_users.resource_exists = AsyncMock(
            return_value="obj_id",
        )
        
        new_cred = ModelV2CredentialPostResult(
            id="cred_id",
            created="2026-06-02",
            description="my key",
            secret="supersecret",
        )
        self.mock_crud_credentials.create = AsyncMock(
            return_value=new_cred,
        )

        response = self.client.post(
            url="/api/v2/users/_self/credentials",
            json={
                "description": "my key",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="cred_id",
        )

    async def test_delete_credential_self(self):
        user = ModelV2UserGet(
            id="test_user",
            admin=False,
        )
        self.mock_authorize.get_user = AsyncMock(
            return_value=user,
        )
        self.mock_crud_credentials.delete = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/users/_self/credentials/cred_id",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
