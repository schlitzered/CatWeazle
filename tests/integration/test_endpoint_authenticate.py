from unittest.mock import AsyncMock
from catweazle.model.v2.users import ModelV2UserGet
from tests.base import EndpointTestCase

class TestEndpointAuthenticate(EndpointTestCase):
    async def test_get_authenticated_success(self):
        user = ModelV2UserGet(
            id="admin",
            admin=True,
        )
        self.mock_authorize.get_user = AsyncMock(
            return_value=user,
        )
        response = self.client.get(
            url="/api/v2/authenticate",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
        self.assertEqual(
            first=response.json(),
            second={
                "user": "admin",
            },
        )

    async def test_login_success(self):
        self.mock_crud_users.check_credentials = AsyncMock(
            return_value="admin",
        )
        response = self.client.post(
            url="/api/v2/authenticate",
            json={
                "user": "admin",
                "password": "password",
            },
        )
        self.assertEqual(
            first=response.status_code,
            second=201,
        )
        self.assertEqual(
            first=response.json(),
            second={
                "user": "admin",
            },
        )

    async def test_logout(self):
        response = self.client.delete(
            url="/api/v2/authenticate",
        )
        self.assertEqual(
            first=response.status_code,
            second=200,
        )
