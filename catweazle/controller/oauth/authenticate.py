import logging

from fastapi import APIRouter
from fastapi import Request
from fastapi import HTTPException
from starlette.responses import RedirectResponse

import httpx

from catweazle.crud.users import CrudUsers
from catweazle.crud.oauth import CrudOAuth

from catweazle.errors import ResourceNotFound
from catweazle.errors import AuthenticationError

from catweazle.model.v2.common import ModelV2MetaMulti
from catweazle.model.oauth import ModelOauthProviderGet
from catweazle.model.oauth import ModelOauthProviderGetMulti
from catweazle.model.v2.users import ModelV2UserPut


class ControllerOauthAuthenticate:
    def __init__(
        self,
        log: logging.Logger,
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
        crud_oauth: dict[str, CrudOAuth],
    ):
        self._crud_users = crud_users
        self._http = http
        self._log = log
        self._crud_oauth = crud_oauth
        self._router = APIRouter(
            prefix="/authenticate",
            tags=["authenticate"],
        )

        self.router.add_api_route(
            "/oauth",
            self.get_oauth_providers,
            response_model=ModelOauthProviderGetMulti,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/oauth/{provider}/login",
            self.get_oauth_login,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/oauth/{provider}/auth",
            self.get_oauth_auth,
            methods=["GET"],
        )

    @property
    def crud_oauth(self):
        return self._crud_oauth

    @property
    def crud_users(self):
        return self._crud_users

    @property
    def http(self):
        return self._http

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    async def get_oauth_providers(self):
        providers = list()
        for provider in self.crud_oauth.keys():
            providers.append(ModelOauthProviderGet(id=provider))
        return ModelOauthProviderGetMulti(
            result=providers, meta=ModelV2MetaMulti(result_size=len(providers))
        )

    async def get_oauth_login(self, provider: str, request: Request):
        provider = self.crud_oauth.get(provider, None)
        if provider is None:
            raise HTTPException(status_code=404, detail="oauth provider not found")
        return await provider.oauth_login(request=request)

    async def get_oauth_auth(
        self,
        provider: str,
        request: Request,
    ):
        _provider = self.crud_oauth.get(provider, None)
        if _provider is None:
            raise HTTPException(status_code=404, detail="oauth provider not found")
        token = await _provider.oauth_auth(request=request)
        userinfo = await _provider.get_user_info(token=token["access_token"])
        login = userinfo["login"]
        try:
            user = await self.crud_users.get(_id=login, fields=["backend"])
            if user.backend != f"oauth:{provider}":
                if _provider.backend_override:
                    self.log.warning(
                        f"backend override: backend:{user.backend} -> oauth:{provider}"
                    )
                    await self.crud_users.update(
                        _id=login,
                        payload=ModelV2UserPut(
                            backend=f"oauth{provider}",
                        ),
                        fields=["_id"],
                    )
                else:
                    self.log.error(
                        f"auth backend mismatch: {user.backend} != {provider}"
                    )
                    raise AuthenticationError(
                        msg="backend mismatch, please contact the administrator"
                    )
        except ResourceNotFound:
            await self.crud_users.create_external(
                _id=login,
                payload=ModelV2UserPut(
                    admin=False,
                    email=userinfo["email"],
                    name=userinfo["name"],
                ),
                fields=["_id"],
                backend=f"oauth:{provider}",
            )
        request.session["username"] = login
        return RedirectResponse(url="/")
