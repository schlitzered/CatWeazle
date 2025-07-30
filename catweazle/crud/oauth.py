import logging

from authlib.integrations.starlette_client import OAuth as authlibOauth

import httpx


class CrudOAuth:
    def __init__(
        self,
        log: logging.Logger,
        http: httpx.AsyncClient,
        backend_override: bool,
        name: str,
        oauth: authlibOauth,
        scope: str,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        access_token_url: str,
    ):
        self._backend_override = backend_override
        self._http = http
        self._log = log
        self._name = name
        self._oauth = oauth
        self._scope = scope
        self.oauth.register(
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=authorize_url,
            access_token_url=access_token_url,
            client_kwargs={"scope": scope},
        )

    @property
    def backend_override(self):
        return self._backend_override

    @property
    def http(self):
        return self._http

    @property
    def log(self):
        return self._log

    @property
    def name(self):
        return self._name

    @property
    def oauth(self):
        return self._oauth

    @property
    def scope(self):
        return self._scope

    async def oauth_login(self, request):
        redirect_url = request.url_for("get_oauth_auth", provider=self.name)
        provider = self.oauth.create_client(name=self.name)
        return await provider.authorize_redirect(request, str(redirect_url))

    async def oauth_auth(self, request):
        provider = self.oauth.create_client(name=self.name)
        token = await provider.authorize_access_token(request)
        return token

    async def get_user_info(self, token):
        raise NotImplementedError


class CrudOAuthGitHub(CrudOAuth):
    def __init__(
        self,
        log: logging.Logger,
        http: httpx.AsyncClient,
        backend_override: bool,
        name: str,
        oauth: authlibOauth,
        scope: str,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        access_token_url: str,
        userinfo_url: str,
    ):
        super(CrudOAuthGitHub, self).__init__(
            log=log,
            http=http,
            backend_override=backend_override,
            name=name,
            oauth=oauth,
            scope=scope,
            client_id=client_id,
            client_secret=client_secret,
            authorize_url=authorize_url,
            access_token_url=access_token_url,
        )

        self._userinfo_url = userinfo_url

    @property
    def userinfo_url(self):
        return self._userinfo_url

    async def get_user_info(self, token: str):
        user_info = await self.http.get(
            url=self.userinfo_url, headers={"Authorization": f"token {token}"}
        )
        return user_info.json()
