__author__ = 'schlitzer'
from aiohttp.web import json_response
import jsonschema
import jsonschema.exceptions

from catweazle.errors import ResourceNotFound
from catweazle.schemes import CREDENTIALS_CREATE
from catweazle.schemes import USERS_CREATE, USERS_UPDATE


class Users:
    def __init__(self, aa, credentials, permissions, users):
        self._aa = aa
        self._credentials = credentials
        self._permissions = permissions
        self._users = users

    @property
    def aa(self):
        return self._aa

    @property
    def credentials(self):
        return self._credentials

    @property
    def permissions(self):
        return self._permissions

    @property
    def users(self):
        return self._users

    async def delete(self, request):
        user = request.match_info['user']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
            await self.users.delete_mark(user)
            await self.permissions.delete_user_from_all(user)
            await self.credentials.delete_all_from_owner(user)
        return json_response(await self.users.delete(user))

    async def get(self, request):
        user = request.match_info['user']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        fields = request.query.get('fields', None)
        return json_response(await self.users.get(user, fields))

    async def post(self, request):
        user = request.match_info['user']
        await self.aa.require_admin(request)
        payload = await request.json()
        jsonschema.validate(payload, USERS_CREATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        if 'admin' not in payload:
            payload['admin'] = False
        payload['backend'] = 'internal'
        payload['backend_ref'] = user
        result = await self.users.create(user, payload)
        return json_response(result, status=201)

    async def put(self, request):
        user = request.match_info['user']
        payload = await request.json()
        jsonschema.validate(payload, USERS_UPDATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        if user == '_self':
            payload.pop('admin', None)
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        return json_response(await self.users.update(user, payload))

    async def search(self, request):
        await self.aa.require_admin(request)
        result = await self.users.search(
            _id=request.query.get('id', None),
            fields=request.query.get('fields', None),
            sort=request.query.get('sort', None),
            page=request.query.get('page', None),
            limit=request.query.get('limit', None)
        )
        return json_response(result)


class UsersCredentials:
    def __init__(self, aa, users, credentials):
        self._aa = aa
        self._credentials = credentials
        self._users = users

    @property
    def aa(self):
        return self._aa

    @property
    def credentials(self):
        return self._credentials

    @property
    def users(self):
        return self._users

    async def delete(self, request):
        user = request.match_info['user']
        cred = request.match_info['cred']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        if not await self.users.resource_exists(user):
            raise ResourceNotFound(user)
        return json_response(await self.credentials.delete(cred, user))

    async def get(self, request):
        user = request.match_info['user']
        cred = request.match_info['cred']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        if not await self.users.resource_exists(user):
            raise ResourceNotFound(user)
        return json_response(await self.credentials.get(cred, user))

    async def get_all(self, request):
        user = request.match_info['user']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        if not await self.users.resource_exists(user):
            raise ResourceNotFound(user)
        return json_response(await self.credentials.get_all(user))

    async def post(self, request):
        user = request.match_info['user']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        payload = await request.json()
        jsonschema.validate(payload, CREDENTIALS_CREATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        if not await self.users.resource_exists(user):
            raise ResourceNotFound(user)
        return json_response(await self.credentials.create(user, payload), status=201)

    async def put(self, request):
        user = request.match_info['user']
        cred = request.match_info['cred']
        if user == '_self':
            user = await self.aa.get_user(request)
        else:
            await self.aa.require_admin(request)
        payload = await request.json()
        jsonschema.validate(payload, CREDENTIALS_CREATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        if not await self.users.resource_exists(user):
            raise ResourceNotFound(user)
        return json_response(await self.credentials.update(cred, user, payload), status=201)
