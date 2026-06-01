import logging
import typing
import httpx
import json
import re
import tempfile
import os
import shutil
import base64
import hashlib

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorCollection
import pymongo

from catweazle.crud.common import CrudMongo
from catweazle.crud.secrets import CrudSecrets
from catweazle.model.v2.common import ModelV2DataDelete
from catweazle.model.v2.common import sort_order_literal
from catweazle.model.v2.webhooks import ModelV2WebhookGet
from catweazle.model.v2.webhooks import ModelV2WebhookGetMulti
from catweazle.model.v2.webhooks import ModelV2WebhookPost
from catweazle.model.v2.webhooks import ModelV2WebhookPut


class CrudWebhooks(CrudMongo):
    def __init__(
        self, log: logging.Logger, coll: AsyncIOMotorCollection, encryption_key: str
    ):
        super(CrudWebhooks, self).__init__(log=log, coll=coll)
        key = base64.urlsafe_b64encode(hashlib.sha256(encryption_key.encode()).digest())
        self._fernet = Fernet(key)

    async def index_create(self) -> None:
        self.log.info(f"creating {self.resource_type} indices")
        await self.coll.create_index([("id", pymongo.ASCENDING)], unique=True)
        self.log.info(f"creating {self.resource_type} indices, done")

    def _encrypt(self, data: str) -> str:
        if not data:
            return data
        return self._fernet.encrypt(data.encode()).decode()

    def _decrypt(self, data: str) -> str:
        if not data:
            return data
        return self._fernet.decrypt(data.encode()).decode()

    async def create(
        self, payload: ModelV2WebhookPost, fields: list
    ) -> ModelV2WebhookGet:
        data = payload.model_dump()
        if data.get("password"):
            data["password"] = self._encrypt(data["password"])
        if data.get("ssl_key"):
            data["ssl_key"] = self._encrypt(data["ssl_key"])
        result = await self._create(payload=data, fields=fields)
        return ModelV2WebhookGet(**result)

    async def delete(self, _id: str) -> ModelV2DataDelete:
        query = {"id": _id}
        await self._delete(query=query)
        return ModelV2DataDelete()

    async def get(self, _id: str, fields: list) -> ModelV2WebhookGet:
        query = {"id": _id}
        result = await self._get(query=query, fields=fields)
        return ModelV2WebhookGet(**result)

    async def search(
        self,
        _id: typing.Optional[str] = None,
        fields: typing.Optional[list] = None,
        sort: typing.Optional[str] = None,
        sort_order: typing.Optional[sort_order_literal] = None,
        page: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        query: typing.Optional[dict] = None,
    ) -> ModelV2WebhookGetMulti:
        if not query:
            query = {}
        self._filter_re(query, "id", _id)
        result = await self._search(
            query=query,
            fields=fields,
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return ModelV2WebhookGetMulti(
            result=result["result"], meta={"result_size": result["count"]}
        )

    async def update(
        self, _id: str, payload: ModelV2WebhookPut, fields: list
    ) -> ModelV2WebhookGet:
        query = {"id": _id}
        data = payload.model_dump(exclude_unset=True)
        if data.get("password"):
            data["password"] = self._encrypt(data["password"])
        if data.get("ssl_key"):
            data["ssl_key"] = self._encrypt(data["ssl_key"])
        result = await self._update(query=query, fields=fields, payload=data)
        return ModelV2WebhookGet(**result)

    async def execute(
        self,
        trigger: str,
        instance_data: dict,
        crud_secrets: CrudSecrets,
        http_client: httpx.AsyncClient,
    ):
        query = {"triggers": trigger}
        webhooks = await self.search(query=query)

        for webhook in webhooks.result:
            try:
                await self._execute_one(
                    webhook=webhook,
                    instance_data=instance_data,
                    crud_secrets=crud_secrets,
                    http_client=http_client,
                )
            except Exception as e:
                self.log.error(f"Failed to execute webhook {webhook.id}: {e}")
                if webhook.fail_on_error and trigger.startswith("pre-"):
                    raise e

    async def _execute_one(
        self,
        webhook: ModelV2WebhookGet,
        instance_data: dict,
        crud_secrets: CrudSecrets,
        http_client: httpx.AsyncClient,
    ):
        context = {
            "id": instance_data.get("id"),
            "ip_address": instance_data.get("ip_address"),
            "dns_indicator": instance_data.get("dns_indicator"),
            "fqdn": instance_data.get("fqdn"),
            **instance_data.get("meta", {}),
        }

        # Resolve secrets
        secrets_context = {}

        async def resolve_placeholders(text: str) -> str:
            if not text:
                return text

            # Simple placeholder replacement for secrets: {secret:id}
            # and for instance data: {key}

            # Handle secrets first
            secret_pattern = r"\{secret:([a-zA-Z0-9_-]+)\}"
            for match in re.finditer(secret_pattern, text):
                secret_id = match.group(1)
                if secret_id not in secrets_context:
                    try:
                        secrets_context[secret_id] = await crud_secrets.get_secret(
                            secret_id
                        )
                    except Exception:
                        secrets_context[secret_id] = "SECRET_NOT_FOUND"
                text = text.replace(match.group(0), secrets_context[secret_id])

            # Handle instance data
            for key, value in context.items():
                placeholder = "{" + key + "}"
                if placeholder in text:
                    text = text.replace(placeholder, str(value))

            return text

        url = await resolve_placeholders(webhook.url)

        headers = {}
        if webhook.headers:
            for k, v in webhook.headers.items():
                headers[k] = await resolve_placeholders(v)

        params = {}
        if webhook.query_params:
            for k, v in webhook.query_params.items():
                params[k] = await resolve_placeholders(v)

        json_payload = None
        if webhook.payload:
            payload_str = json.dumps(webhook.payload)
            payload_str = await resolve_placeholders(payload_str)
            json_payload = json.loads(payload_str)

        # Auth and mTLS
        auth = None
        if webhook.username:
            # Decrypt password if it exists
            password = ""
            if webhook.password:
                # We need to fetch the encrypted password from DB since ModelV2WebhookGet might not have it or it might be masked
                # But here 'webhook' is from 'search' which returns the raw data from DB into the model.
                # However, our 'get'/'search' doesn't decrypt.
                # Let's fetch the raw document to be sure we have the encrypted fields.
                raw_webhook = await self._get(query={"id": webhook.id}, fields=["password", "ssl_key"])
                password = self._decrypt(raw_webhook.get("password", ""))
            
            auth = (
                await resolve_placeholders(webhook.username),
                await resolve_placeholders(password),
            )

        request_client = http_client
        client_to_close = None
        temp_dir = None

        if webhook.ssl_key or webhook.ssl_cert or webhook.ssl_ca:
            # Fetch raw encrypted fields
            raw_webhook = await self._get(query={"id": webhook.id}, fields=["ssl_key"])
            decrypted_ssl_key = self._decrypt(raw_webhook.get("ssl_key", ""))

            ssl_cert_path = None
            ssl_key_path = None
            ssl_ca_path = True  # Default to True (verify)

            temp_dir = tempfile.mkdtemp()

            try:
                if webhook.ssl_cert:
                    ssl_cert_path = os.path.join(temp_dir, "cert.pem")
                    with open(ssl_cert_path, "w") as f:
                        f.write(webhook.ssl_cert)

                if decrypted_ssl_key:
                    ssl_key_path = os.path.join(temp_dir, "key.pem")
                    with open(ssl_key_path, "w") as f:
                        f.write(decrypted_ssl_key)

                if webhook.ssl_ca:
                    ssl_ca_path = os.path.join(temp_dir, "ca.pem")
                    with open(ssl_ca_path, "w") as f:
                        f.write(webhook.ssl_ca)

                cert = None
                if ssl_cert_path and ssl_key_path:
                    cert = (ssl_cert_path, ssl_key_path)
                elif ssl_cert_path:
                    cert = ssl_cert_path

                request_client = httpx.AsyncClient(
                    cert=cert,
                    verify=ssl_ca_path,
                )
                client_to_close = request_client

            except Exception as e:
                if temp_dir:
                    shutil.rmtree(temp_dir)
                raise e

        self.log.info(f"Executing webhook {webhook.id} ({webhook.method} {url})")

        try:
            response = await request_client.request(
                method=webhook.method,
                url=url,
                headers=headers,
                params=params,
                json=json_payload,
                auth=auth,
                timeout=10.0,
            )
            response.raise_for_status()
        finally:
            if client_to_close:
                await client_to_close.aclose()
            if temp_dir:
                shutil.rmtree(temp_dir)
