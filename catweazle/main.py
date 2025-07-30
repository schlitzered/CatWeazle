from contextlib import asynccontextmanager
import logging
import random
import string
import sys
import time
from typing import List

from authlib.integrations.starlette_client import OAuth
import bonsai.asyncio
import httpx
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

import catweazle.controller
import catweazle.controller.oauth

from catweazle.authorize import Authorize

from catweazle.config import Config
from catweazle.config import ConfigLdap as SettingsLdap
from catweazle.config import ConfigOAuth as SettingsOAuth

from catweazle.crud.credentials import CrudCredentials
from catweazle.crud.ldap import CrudLdap
from catweazle.crud.foreman import CrudForeman
from catweazle.crud.instances import CrudInstances
from catweazle.crud.oauth import CrudOAuthGitHub
from catweazle.crud.permissions import CrudPermissions
from catweazle.crud.users import CrudUsers

from catweazle.model.v2.users import ModelV2UserPost

from catweazle.errors import ResourceNotFound


settings = Config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = setup_logging(
        settings.app.loglevel,
    )

    http = httpx.AsyncClient()

    ldap_pool = await setup_ldap(
        log=log,
        settings_ldap=settings.ldap,
    )

    log.info("adding routes")
    mongo_db = setup_mongodb(
        log=log,
        database=settings.mongodb.database,
        url=settings.mongodb.url,
    )

    crud_foreman_backends = setup_foreman_backend(log=log)

    crud_oauth = setup_oauth_providers(
        log=log,
        http=http,
        oauth_settings=settings.oauth,
    )

    crud_ldap = CrudLdap(
        log=log,
        ldap_base_dn=settings.ldap.basedn,
        ldap_bind_dn=settings.ldap.binddn,
        ldap_pool=ldap_pool,
        ldap_url=settings.ldap.url,
        ldap_user_pattern=settings.ldap.userpattern,
    )

    crud_instances = CrudInstances(
        log=log,
        coll=mongo_db["instances"],
        domain_suffix=settings.app.domain_suffix,
    )
    await crud_instances.index_create()

    crud_permissions = CrudPermissions(
        log=log,
        coll=mongo_db["permissions"],
    )
    await crud_permissions.index_create()

    crud_users = CrudUsers(
        log=log,
        coll=mongo_db["users"],
        crud_ldap=crud_ldap,
    )
    await crud_users.index_create()

    crud_users_credentials = CrudCredentials(
        log=log,
        coll=mongo_db["users_credentials"],
    )
    await crud_users_credentials.index_create()

    authorize = Authorize(
        log=log,
        crud_permissions=crud_permissions,
        crud_users=crud_users,
        crud_users_credentials=crud_users_credentials,
    )

    controller = catweazle.controller.Controller(
        log=log,
        authorize=authorize,
        crud_ldap=crud_ldap,
        crud_foreman_backends=crud_foreman_backends,
        crud_instances=crud_instances,
        crud_permissions=crud_permissions,
        crud_users=crud_users,
        crud_users_credentials=crud_users_credentials,
        crud_oauth=crud_oauth,
        http=http,
    )
    app.include_router(controller.router)

    log.info("adding routes, done")
    await setup_admin_user(log=log, crud_users=crud_users)
    yield


async def setup_admin_user(log: logging.Logger, crud_users: CrudUsers):
    try:
        await crud_users.get(_id="admin", fields=["_id"])
    except ResourceNotFound:
        password = "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(20)
        )
        log.info(f"creating admin user with password {password}")
        await crud_users.create(
            _id="admin",
            payload=ModelV2UserPost(
                admin=True,
                email="admin@example.com",
                name="admin",
                password=password,
            ),
            fields=["_id"],
        )
        log.info("creating admin user, done")


async def setup_ldap(log: logging.Logger, settings_ldap: SettingsLdap):
    if not settings_ldap.url:
        log.info("ldap not configured")
        return
    log.info(f"setting up ldap with {settings_ldap.url} as a backend")
    if not settings_ldap.binddn:
        log.fatal("ldap binddn not configured")
        sys.exit(1)
    if not settings_ldap.password:
        log.fatal("ldap password not configured")
        sys.exit(1)
    client = bonsai.LDAPClient(settings_ldap.url)
    client.set_credentials("SIMPLE", settings_ldap.binddn, settings_ldap.password)
    pool = bonsai.asyncio.AIOConnectionPool(client=client, maxconn=30)
    await pool.open()
    return pool


def setup_foreman_backend(log: logging.Logger) -> List[CrudForeman]:
    if not settings.foreman:
        log.info("no foreman backend configured")
    backends = list()
    realm = False
    if not settings.foreman:
        return backends
    for name, config in settings.foreman.items():
        log.info(f"setting up foreman backend with name {name}")
        if realm and config.realmenable:
            log.fatal("only one realm provider is allowed")
            sys.exit(1)
        if config.realmenable:
            log.info(f"realm provider enabled for {name}")
            realm = True
        backends.append(
            CrudForeman(
                log=log,
                name=name,
                url=config.url,
                ssl_key=config.sslkey,
                ssl_crt=config.sslcrt,
                dns_arpa_enable=config.dnsarpaenable,
                dns_arpa_zones=config.dnsarpazones,
                dns_forward_enable=config.dnsforwardenable,
                realm_enable=config.realmenable,
                realm_name=config.realmname,
            )
        )
    return backends


def setup_logging(log_level):
    log = logging.getLogger("uvicorn")
    log.info(f"setting loglevel to: {log_level}")
    log.setLevel(log_level)
    return log


def setup_mongodb(log: logging.Logger, database: str, url: str) -> AsyncIOMotorDatabase:
    log.info("setting up mongodb client")
    pool = AsyncIOMotorClient(url)
    db = pool.get_database(database)
    log.info("setting up mongodb client, done")
    return db


def setup_oauth_providers(
    log: logging.Logger,
    http: httpx.AsyncClient,
    oauth_settings: dict["str", SettingsOAuth],
):
    oauth = OAuth()
    providers = {}
    if not oauth_settings:
        log.info("oauth not configured")
        return providers
    for provider, config in oauth_settings.items():
        if config.type == "github":
            log.info(f"oauth setting up github provider with name {provider}")
            providers[provider] = CrudOAuthGitHub(
                log=log,
                http=http,
                backend_override=config.override,
                name=provider,
                oauth=oauth,
                scope=config.scope,
                client_id=config.client.id,
                client_secret=config.client.secret,
                authorize_url=config.url.authorize,
                access_token_url=config.url.accesstoken,
                userinfo_url=config.url.userinfo,
            )
    return providers


app = FastAPI(title="catweazle", version="0.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.app.secretkey, max_age=3600)


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


def main():
    uvicorn.run(app, host=settings.app.host, port=settings.app.port)


if __name__ == "__main__":
    main()
