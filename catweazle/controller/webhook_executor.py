import logging
import typing
import httpx
import json
import re
import tempfile
import shutil

from catweazle.crud.secrets import CrudSecrets
from catweazle.crud.webhook_logs import CrudWebhookLogs
from catweazle.crud.webhooks import CrudWebhooks
from catweazle.errors import BackendError
from catweazle.errors import ResourceNotFound
from catweazle.model.v2.webhooks import ModelV2WebhookGet

REDACTED_SECRET = "<redacted secret>"


class WebhookExecutor:

    def __init__(
        self,
        *,
        log: logging.Logger,
        crud_webhooks: CrudWebhooks,
        crud_secrets: CrudSecrets,
        crud_webhook_logs: CrudWebhookLogs,
        http_client: httpx.AsyncClient,
    ):
        self._log = log
        self._crud_webhooks = crud_webhooks
        self._crud_secrets = crud_secrets
        self._crud_webhook_logs = crud_webhook_logs
        self._http_client = http_client

    @staticmethod
    def _redact_secrets(
        *,
        text: str,
        secret_values: typing.Set[str],
    ) -> str:
        if not text:
            return text
        for secret_value in secret_values:
            text = text.replace(
                secret_value,
                REDACTED_SECRET,
            )
        return text

    def _redact_dict(
        self,
        *,
        data: dict,
        secret_values: typing.Set[str],
    ) -> dict:
        if not data:
            return data
        redacted = {}
        for k, v in data.items():
            if type(v) is str:
                redacted[k] = self._redact_secrets(
                    text=v,
                    secret_values=secret_values,
                )
            else:
                redacted[k] = v
        return redacted

    async def execute(
        self,
        *,
        trigger: str,
        instance_data: dict,
    ) -> None:
        query = {
            "triggers": trigger,
        }
        webhooks = await self._crud_webhooks.search(
            query=query,
        )
        for webhook in webhooks.result:
            try:
                await self._execute_one(
                    webhook=webhook,
                    trigger=trigger,
                    instance_data=instance_data,
                )
            except (httpx.HTTPError, BackendError) as e:
                self._log.error(
                    f"Failed to execute webhook {webhook.id}: {e}"
                )
                if webhook.fail_on_error and trigger.startswith("pre-"):
                    raise e

    async def _execute_one(
        self,
        *,
        webhook: ModelV2WebhookGet,
        trigger: str,
        instance_data: dict,
    ) -> None:
        meta = instance_data.get("meta")
        if not meta:
            meta = {}
        context = {
            "id": instance_data.get("id"),
            "ip_address": instance_data.get("ip_address"),
            "dns_indicator": instance_data.get("dns_indicator"),
            "fqdn": instance_data.get("fqdn"),
            **meta,
        }
        instance_id = instance_data.get("id")
        if not instance_id:
            instance_id = ""
        secrets_context = {}
        resolved_secret_values = set()

        async def resolve_placeholders(
            *,
            text: str,
        ) -> str:
            if not text:
                return text
            secret_pattern = r"\{secret:([a-zA-Z0-9_-]+)\}"
            for match in re.finditer(
                pattern=secret_pattern,
                string=text,
            ):
                secret_id = match.group(1)
                if secret_id not in secrets_context:
                    try:
                        secrets_context[secret_id] = await self._crud_secrets.get_secret(
                            _id=secret_id,
                        )
                        resolved_secret_values.add(
                            secrets_context[secret_id],
                        )
                    except (ResourceNotFound, BackendError):
                        secrets_context[secret_id] = "SECRET_NOT_FOUND"
                text = text.replace(
                    match.group(0),
                    secrets_context[secret_id],
                )
            for key, value in context.items():
                placeholder = "{" + key + "}"
                if placeholder in text:
                    text = text.replace(
                        placeholder,
                        str(value),
                    )
            return text

        url = await resolve_placeholders(
            text=webhook.url,
        )
        headers = {}
        if webhook.headers:
            for k, v in webhook.headers.items():
                headers[k] = await resolve_placeholders(
                    text=v,
                )
        params = {}
        if webhook.query_params:
            for k, v in webhook.query_params.items():
                params[k] = await resolve_placeholders(
                    text=v,
                )
        json_payload = None
        if webhook.payload:
            payload_str = json.dumps(
                obj=webhook.payload,
            )
            payload_str = await resolve_placeholders(
                text=payload_str,
            )
            json_payload = json.loads(
                s=payload_str,
            )
        auth = None
        if webhook.username:
            password = ""
            if webhook.password:
                raw_webhook = await self._crud_webhooks._get(
                    query={
                        "id": webhook.id,
                    },
                    fields=[
                        "password",
                        "ssl_key",
                    ],
                )
                raw_password = raw_webhook.get("password")
                if not raw_password:
                    raw_password = ""
                password = self._crud_webhooks.decrypt(
                    data=raw_password,
                )
            auth_username = await resolve_placeholders(
                text=webhook.username,
            )
            auth_password = await resolve_placeholders(
                text=password,
            )
            auth = (
                auth_username,
                auth_password,
            )
        request_client = self._http_client
        client_to_close = None
        temp_dir = None
        if webhook.ssl_key or webhook.ssl_cert or webhook.ssl_ca:
            raw_webhook = await self._crud_webhooks._get(
                query={
                    "id": webhook.id,
                },
                fields=[
                    "ssl_key",
                ],
            )
            raw_ssl_key = raw_webhook.get("ssl_key")
            if not raw_ssl_key:
                raw_ssl_key = ""
            decrypted_ssl_key = self._crud_webhooks.decrypt(
                data=raw_ssl_key,
            )
            ssl_cert_path = None
            ssl_key_path = None
            ssl_ca_path = True
            temp_dir = tempfile.mkdtemp()
            try:
                if webhook.ssl_cert:
                    ssl_cert_path = f"{temp_dir}/cert.pem"
                    with open(
                        file=ssl_cert_path,
                        mode="w",
                    ) as f:
                        f.write(
                            webhook.ssl_cert,
                        )
                if decrypted_ssl_key:
                    ssl_key_path = f"{temp_dir}/key.pem"
                    with open(
                        file=ssl_key_path,
                        mode="w",
                    ) as f:
                        f.write(
                            decrypted_ssl_key,
                        )
                if webhook.ssl_ca:
                    ssl_ca_path = f"{temp_dir}/ca.pem"
                    with open(
                        file=ssl_ca_path,
                        mode="w",
                    ) as f:
                        f.write(
                            webhook.ssl_ca,
                        )
                cert = None
                if ssl_cert_path and ssl_key_path:
                    cert = (
                        ssl_cert_path,
                        ssl_key_path,
                    )
                elif ssl_cert_path:
                    cert = ssl_cert_path
                request_client = httpx.AsyncClient(
                    cert=cert,
                    verify=ssl_ca_path,
                )
                client_to_close = request_client
            except (OSError, httpx.HTTPError) as e:
                if temp_dir:
                    shutil.rmtree(
                        path=temp_dir,
                    )
                raise e

        self._log.info(
            f"Executing webhook {webhook.id} ({webhook.method} {url})"
        )
        response = None
        error_msg = None
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
        except (httpx.HTTPError, OSError) as e:
            error_msg = str(e)
            raise e
        finally:
            if client_to_close:
                await client_to_close.aclose()
            if temp_dir:
                shutil.rmtree(
                    path=temp_dir,
                )
            log_request_headers = self._redact_dict(
                data=headers,
                secret_values=resolved_secret_values,
            )
            log_request_params = self._redact_dict(
                data=params,
                secret_values=resolved_secret_values,
            )
            log_request_body = None
            if json_payload:
                log_request_body_str = json.dumps(
                    obj=json_payload,
                )
                redacted_body_str = self._redact_secrets(
                    text=log_request_body_str,
                    secret_values=resolved_secret_values,
                )
                log_request_body = json.loads(
                    s=redacted_body_str,
                )
            log_response_status_code = None
            log_response_headers = None
            log_response_body = None
            if response is not None:
                log_response_status_code = response.status_code
                log_response_headers = dict(
                    response.headers,
                )
                log_response_body = response.text
            try:
                await self._crud_webhook_logs.create(
                    instance_id=instance_id,
                    webhook_id=webhook.id,
                    trigger=trigger,
                    url=url,
                    method=webhook.method,
                    request_headers=log_request_headers,
                    request_params=log_request_params,
                    request_body=log_request_body,
                    response_status_code=log_response_status_code,
                    response_headers=log_response_headers,
                    response_body=log_response_body,
                    error=error_msg,
                )
            except BackendError:
                self._log.error(
                    f"failed to store webhook log for {webhook.id}"
                )
