from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from catweazle.model.v2.users import ModelV2UserGet
from catweazle.model.v2.permissions import ModelV2PermissionGet
from tests.base import EndpointTestCase

class TestEndpointPermissions(EndpointTestCase):
    async def test_create_permission_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_admin = AsyncMock(
            return_value=user,
        )

        mock_permission = ModelV2PermissionGet(
            id="perm1",
            users=["test_user"],
            permissions=["INSTANCE:POST"],
        )
        self.mock_crud_permissions.create = AsyncMock(
            return_value=mock_permission,
        )

        response = self.client.post(
            url="/api/v2/permissions/perm1",
            json={
                "users": ["test_user"],
                "permissions": ["INSTANCE:POST"],
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json().get("id"),
            second="perm1",
        )

    async def test_delete_permission_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.require_admin = AsyncMock(
            return_value=user,
        )
        self.mock_crud_permissions.delete = AsyncMock(
            return_value={},
        )

        response = self.client.delete(
            url="/api/v2/permissions/perm1",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
