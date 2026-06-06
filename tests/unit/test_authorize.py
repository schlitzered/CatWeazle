import unittest
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from fastapi import Request
from catweazle.authorize import Authorize
from catweazle.errors import AdminError
from catweazle.errors import SessionCredentialError
from catweazle.model.v2.users import ModelV2UserGet

class TestAuthorize(IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_log = MagicMock()
        self.mock_crud_permissions = MagicMock()
        self.mock_crud_users = MagicMock()
        self.mock_crud_credentials = MagicMock()
        self.authorize = Authorize(
            log=self.mock_log,
            crud_permissions=self.mock_crud_permissions,
            crud_users=self.mock_crud_users,
            crud_users_credentials=self.mock_crud_credentials,
        )

    async def test_get_user_from_session_success(self):
        request = MagicMock(spec=Request)
        request.session = {
            "username": "test_user",
        }
        self.mock_crud_users.get = AsyncMock(
            return_value=ModelV2UserGet(
                id="test_user",
                admin=False,
            ),
        )
        user = await self.authorize.get_user(request=request)
        self.assertEqual(
            first=user.id,
            second="test_user",
        )

    async def test_get_user_from_credentials_success(self):
        request = MagicMock(spec=Request)
        request.session = {}
        self.mock_crud_credentials.check_credential = AsyncMock(
            return_value="test_user",
        )
        self.mock_crud_users.get = AsyncMock(
            return_value=ModelV2UserGet(
                id="test_user",
                admin=False,
            ),
        )
        user = await self.authorize.get_user(request=request)
        self.assertEqual(
            first=user.id,
            second="test_user",
        )

    async def test_get_user_fails(self):
        request = MagicMock(spec=Request)
        request.session = {}
        self.mock_crud_credentials.check_credential = AsyncMock(
            return_value=None,
        )
        with self.assertRaises(
            expected_exception=SessionCredentialError,
        ):
            await self.authorize.get_user(request=request)

    async def test_require_admin_success(self):
        user = ModelV2UserGet(
            id="admin_user",
            admin=True,
        )
        res = await self.authorize.require_admin(
            request=MagicMock(spec=Request),
            user=user,
        )
        self.assertEqual(
            first=res.id,
            second="admin_user",
        )

    async def test_require_admin_raises_error(self):
        user = ModelV2UserGet(
            id="normal_user",
            admin=False,
        )
        with self.assertRaises(
            expected_exception=AdminError,
        ):
            await self.authorize.require_admin(
                request=MagicMock(spec=Request),
                user=user,
            )
