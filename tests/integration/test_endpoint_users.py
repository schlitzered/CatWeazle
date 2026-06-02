from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from catweazle.model.v2.users import ModelV2UserGet
from tests.base import EndpointTestCase

class TestEndpointUsers(EndpointTestCase):
    async def test_create_user_success(self):
        admin_user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_admin = AsyncMock(
            return_value=admin_user,
        )
        
        new_user = ModelV2UserGet(
            id="new_user",
            admin=False,
            email="new@example.com",
            name="New User",
        )
        self.mock_crud_users.create = AsyncMock(
            return_value=new_user,
        )

        response = self.client.post(
            url="/api/v2/users/new_user",
            json={
                "email": "new@example.com",
                "name": "New User",
                "password": "somepassword123",
                "admin": False,
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="new_user",
        )

    async def test_get_user_success(self):
        admin_user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_admin = AsyncMock(
            return_value=admin_user,
        )

        target_user = ModelV2UserGet(
            id="target",
            admin=False,
            email="target@example.com",
            name="Target User",
        )
        self.mock_crud_users.get = AsyncMock(
            return_value=target_user,
        )

        response = self.client.get(
            url="/api/v2/users/target",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="target",
        )

    async def test_delete_user_success(self):
        admin_user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_admin = AsyncMock(
            return_value=admin_user,
        )
        self.mock_crud_users.delete = AsyncMock(
            return_value={},
        )
        self.mock_crud_credentials.delete_all_from_owner = AsyncMock(
            return_value={},
        )
        self.mock_crud_permissions.delete_user_from_permissions = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/users/target",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
