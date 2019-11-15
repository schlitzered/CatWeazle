__author__ = 'schlitzer'

from catweazle.errors import PermError, CredentialError, SessionCredentialError, AdminError
from catweazle.errors import SessionError


class AuthenticationAuthorization(object):
    def __init__(self, users, users_credentials, permissions, sessions):
        self.users = users
        self.users_credentials = users_credentials
        self.sessions = sessions
        self.permissions = permissions

    async def get_user_from_session(self, request):
        result = await self.sessions.get_user(request)
        return result['data']['user']

    @staticmethod
    async def get_user_credential(request):
        result = {}
        _id = request.headers.get('X-ID', False)
        secret = request.headers.get('X-SECRET', False)
        if _id and secret:
            result['id'] = _id
            result['secret'] = secret
            return result
        raise CredentialError

    async def get_user_from_credential(self, request):
        credential = await self.get_user_credential(request)
        return await self.users_credentials.check_credential(credential)

    async def get_user(self, request):
        try:
            user = await self.get_user_from_session(request)
        except SessionError:
            try:
                user = await self.get_user_from_credential(request)
                user = user['data']['user']
            except CredentialError:
                raise SessionCredentialError
        return user

    async def require_admin(self, request):
        _is_admin = await self.users.is_admin(await self.get_user(request))
        if not _is_admin:
            raise AdminError
        return True

    async def require(self, request, permission):
        user = await self.get_user(request)
        try:
            return await self.require_admin(request)
        except AdminError:
            try:
                await self.permissions.check(
                    user=user,
                    permission=permission,
                    fields='id'
                )
                return True
            except PermError as err:
                raise err

