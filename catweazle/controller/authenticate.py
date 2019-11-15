__author__ = 'schlitzer'
import json
import jsonschema
import jsonschema.exceptions

from aiohttp.web import json_response, Response

from catweazle.schemes import AUTHENTICATE_CREATE


class Authenticate:
    def __init__(self, sessions, users):
        self._sessions = sessions
        self._users = users

    @property
    def sessions(self):
        return self._sessions

    @property
    def users(self):
        return self._users

    async def delete(self, request):
        await self.sessions.delete(request)
        response = Response()
        response.set_status(204)
        response.del_cookie('DEPLOYER_SESSION')
        return response

    async def get(self, request):
        result = await self.sessions.get_user(request)
        return json_response(result)

    async def post(self, request):
        payload = await request.json()
        jsonschema.validate(payload, AUTHENTICATE_CREATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        user = await self.users.check_credentials(payload)
        result = await self.sessions.create(user)
        response = Response(text=json.dumps(result))
        response.content_type = 'application/json'
        response.set_status(201)
        response.set_cookie(
            'DEPLOYER_SESSION', result['data']['id'],
            httponly=True
        )
        return response
