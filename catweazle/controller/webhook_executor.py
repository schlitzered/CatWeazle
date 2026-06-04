import logging
import typing
import httpx
import json
import re
import tempfile
import ssl

from catweazle.crud.secrets import CrudSecrets
from catweazle.crud.webhook_logs import CrudWebhookLogs
from catweazle.crud.webhooks import CrudWebhooks
from catweazle.errors import BackendError
from catweazle.errors import ResourceNotFound
from catweazle.errors import WebhookExecutionError
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

    def _redact(
        self,
        *,
        data: typing.Any,
        secret_values: typing.Set[str],
    ) -> typing.Any:
        if not data:
            return data
        if isinstance(
            data,
            str,
        ):
            for secret_value in secret_values:
                data = data.replace(
                    secret_value,
                    REDACTED_SECRET,
                )
            return data
        if isinstance(
            data,
            dict,
        ):
            return {
                k: self._redact(
                    data=v,
                    secret_values=secret_values,
                )
                for k, v in data.items()
            }
        if isinstance(
            data,
            (list, tuple),
        ):
            return [
                self._redact(
                    data=item,
                    secret_values=secret_values,
                )
                for item in data
            ]
        return data

    async def _resolve_placeholders(
        self,
        *,
        text: str,
        context: dict,
        secrets_context: dict,
        resolved_secret_values: typing.Set[str],
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
                    secret_value = await self._crud_secrets.get_secret(
                        _id=secret_id,
                    )
                    secrets_context[secret_id] = secret_value
                    resolved_secret_values.add(
                        secret_value,
                    )
                except (ResourceNotFound, BackendError):
                    secrets_context[secret_id] = "SECRET_NOT_FOUND"
            text = text.replace(
                match.group(0),
                secrets_context[secret_id],
            )
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            if placeholder in text:
                text = text.replace(
                    placeholder,
                    str(value),
                )
        return text

    async def _get_ssl_context(
        self,
        *,
        webhook: ModelV2WebhookGet,
    ) -> typing.Optional[ssl.SSLContext]:
        ssl_ctx = None
        if webhook.ssl_ca:
            ssl_ctx = ssl.create_default_context(
                purpose=ssl.Purpose.SERVER_AUTH,
            )
            ssl_ctx.load_verify_locations(
                cadata=webhook.ssl_ca,
            )

        if webhook.ssl_cert and webhook.ssl_key:
            if not ssl_ctx:
                ssl_ctx = ssl.create_default_context(
                    purpose=ssl.Purpose.SERVER_AUTH,
                )
            with tempfile.NamedTemporaryFile(
                mode="w",
            ) as f:
                f.write(
                    webhook.ssl_cert,
                )
                f.write(
                    "\n",
                )
                f.write(
                    self._crud_webhooks.decrypt(
                        data=webhook.ssl_key,
                    ),
                )
                f.flush()
                ssl_ctx.load_cert_chain(
                    certfile=f.name,
                )
        return ssl_ctx

    async def _resolve_webhook_data(
        self,
        *,
        webhook: ModelV2WebhookGet,
        context: dict,
        secrets_context: dict,
        resolved_secret_values: typing.Set[str],
    ) -> dict:
        url = await self._resolve_placeholders(
            text=webhook.url,
            context=context,
            secrets_context=secrets_context,
            resolved_secret_values=resolved_secret_values,
        )
        headers = {}
        if webhook.headers:
            for k, v in webhook.headers.items():
                headers[k] = await self._resolve_placeholders(
                    text=v,
                    context=context,
                    secrets_context=secrets_context,
                    resolved_secret_values=resolved_secret_values,
                )
        params = {}
        if webhook.query_params:
            for k, v in webhook.query_params.items():
                params[k] = await self._resolve_placeholders(
                    text=v,
                    context=context,
                    secrets_context=secrets_context,
                    resolved_secret_values=resolved_secret_values,
                )
        json_payload = None
        if webhook.payload:
            payload_str = await self._resolve_placeholders(
                text=json.dumps(
                    obj=webhook.payload,
                ),
                context=context,
                secrets_context=secrets_context,
                resolved_secret_values=resolved_secret_values,
            )
            json_payload = json.loads(
                s=payload_str,
            )
        auth = None
        if webhook.username:
            auth = (
                await self._resolve_placeholders(
                    text=webhook.username,
                    context=context,
                    secrets_context=secrets_context,
                    resolved_secret_values=resolved_secret_values,
                ),
                await self._resolve_placeholders(
                    text=self._crud_webhooks.decrypt(
                        data=webhook.password,
                    ),
                    context=context,
                    secrets_context=secrets_context,
                    resolved_secret_values=resolved_secret_values,
                ),
            )
        resolved = {
            "url": url,
            "headers": headers,
            "params": params,
            "json_payload": json_payload,
            "auth": auth,
        }
        return {
            "resolved": resolved,
            "redacted": self._redact(
                data=resolved,
                secret_values=resolved_secret_values,
            ),
        }

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
            except (
                httpx.HTTPError,
                OSError,
                BackendError,
            ) as e:
                self._log.error(
                    msg=f"Failed to execute webhook {webhook.id}: {e}",
                )
                if webhook.fail_on_error:
                    raise WebhookExecutionError(
                        webhook_id=webhook.id,
                    ) from e

    async def _execute_one(
        self,
        *,
        webhook: ModelV2WebhookGet,
        trigger: str,
        instance_data: dict,
    ) -> None:
        meta = instance_data.get("meta") or {}
        context = {
            "id": instance_data.get("id"),
            "ip_address": instance_data.get("ip_address"),
            "dns_indicator": instance_data.get("dns_indicator"),
            "fqdn": instance_data.get("fqdn"),
            "instance:id": instance_data.get("id"),
            "instance:ip_address": instance_data.get("ip_address"),
            "instance:dns_indicator": instance_data.get("dns_indicator"),
            "instance:fqdn": instance_data.get("fqdn"),
            "trigger": trigger,
            **{k: v for k, v in meta.items()},
            **{f"instance:meta:{k}": v for k, v in meta.items()},
        }
        instance_id = instance_data.get("id") or ""
        secrets_context = {}
        resolved_secret_values = set()

        data = await self._resolve_webhook_data(
            webhook=webhook,
            context=context,
            secrets_context=secrets_context,
            resolved_secret_values=resolved_secret_values,
        )
        resolved = data["resolved"]
        redacted = data["redacted"]

        response = None
        error_msg = None
        ssl_ctx = await self._get_ssl_context(
            webhook=webhook,
        )

        client = self._http_client
        client_to_close = None
        if ssl_ctx:
            client = httpx.AsyncClient(
                verify=ssl_ctx,
            )
            client_to_close = client

        self._log.info(
            f"Executing webhook {webhook.id} ({webhook.method} {resolved['url']})"
        )
        try:
            response = await client.request(
                method=webhook.method,
                url=resolved["url"],
                headers=resolved["headers"],
                params=resolved["params"],
                json=resolved["json_payload"],
                auth=resolved["auth"],
                timeout=10.0,
            )
            response.raise_for_status()
            self._log.info(
                f"Successfully executed webhook {webhook.id}: HTTP {response.status_code}"
            )
        except (httpx.HTTPError, OSError) as e:
            error_msg = str(e)
            raise e
        finally:
            if client_to_close:
                await client_to_close.aclose()

            try:
                await self._crud_webhook_logs.create(
                    instance_id=instance_id,
                    webhook_id=webhook.id,
                    trigger=trigger,
                    url=redacted["url"],
                    method=webhook.method,
                    request_headers=redacted["headers"],
                    request_params=redacted["params"],
                    request_body=redacted["json_payload"],
                    response_status_code=response.status_code if response else None,
                    response_headers=dict(response.headers) if response else None,
                    response_body=response.text if response else None,
                    error=error_msg,
                )
            except BackendError:
                self._log.error(
                    f"failed to store webhook log for {webhook.id}"
                )
