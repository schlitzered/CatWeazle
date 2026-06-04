import http.server
import json
import sys
import threading
import time
import httpx

class DummyHandler(http.server.BaseHTTPRequestHandler):
    def do_request(self):
        if self.path == "/webhook-fail-4xx":
            self.send_response(code=400)
            self.end_headers()
            return
        if self.path == "/webhook-fail-5xx":
            self.send_response(code=500)
            self.end_headers()
            return
        content_length_str = self.headers.get("Content-Length")
        content_length = 0
        if content_length_str:
            content_length = int(content_length_str)
        body = ""
        if content_length:
            body = self.rfile.read(content_length).decode()
        sys.stdout.write("--- RECEIVED WEBHOOK EVENT ---\n")
        sys.stdout.write(f"Method: {self.command}\n")
        sys.stdout.write(f"Path: {self.path}\n")
        sys.stdout.write("Headers:\n")
        for k, v in self.headers.items():
            sys.stdout.write(f"  {k}: {v}\n")
        if body:
            sys.stdout.write(f"Body: {body}\n")
        sys.stdout.write("-------------------------------\n")
        self.send_response(code=200)
        self.end_headers()

    def do_GET(self):
        self.do_request()

    def do_POST(self):
        self.do_request()

    def do_PUT(self):
        self.do_request()

    def do_DELETE(self):
        self.do_request()

def run():
    server = http.server.HTTPServer(
        server_address=("localhost", 8888),
        RequestHandlerClass=DummyHandler,
    )
    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    client = httpx.Client(
        base_url="http://localhost:3000",
    )

    auth_response = client.post(
        url="/api/v2/authenticate",
        json={
            "user": "admin",
            "password": "password",
        },
    )
    auth_response.raise_for_status()

    cred_response = client.post(
        url="/api/v2/users/admin/credentials",
        json={
            "description": "test webhook key",
        },
    )
    cred_response.raise_for_status()
    cred_data = cred_response.json()
    cred_id = cred_data["id"]
    cred_secret = cred_data["secret"]

    headers = {
        "x-secret-id": cred_id,
        "x-secret": cred_secret,
    }

    # Cleanup existing
    for wh_id in [
        "test-webhook-pre-create",
        "test-webhook-post-create",
        "test-webhook-pre-delete",
        "test-webhook-post-delete",
        "test-webhook-fail-4xx",
        "test-webhook-fail-5xx",
        "test-webhook-secrets",
    ]:
        client.delete(
            url=f"/api/v2/webhooks/{wh_id}",
            headers=headers,
        )
    client.delete(
        url="/api/v2/secrets/test-secret-1",
        headers=headers,
    )

    # Create a secret for testing resolution
    client.post(
        url="/api/v2/secrets",
        json={
            "id": "test-secret-1",
            "secret": "very-secret-value",
            "description": "test secret for webhooks",
        },
        headers=headers,
    ).raise_for_status()

    webhooks_to_create = [
        {
            "id": "test-webhook-pre-create",
            "url": "http://localhost:8888/webhook",
            "method": "GET",
            "triggers": ["pre-create"],
            "headers": {
                "X-Trigger": "{trigger}",
                "X-Instance-ID": "{instance:id}",
            },
            "query_params": {
                "fqdn": "{instance:fqdn}",
                "ip": "{instance:ip_address}",
                "role": "{instance:meta:role}",
            },
        },
        {
            "id": "test-webhook-post-create",
            "url": "http://localhost:8888/webhook",
            "method": "POST",
            "triggers": ["post-create"],
            "headers": {
                "X-Trigger": "{trigger}",
                "X-Instance-ID": "{instance:id}",
            },
            "query_params": {
                "fqdn": "{instance:fqdn}",
                "ip": "{instance:ip_address}",
                "role": "{instance:meta:role}",
            },
            "payload": {
                "msg": "Instance created successfully",
                "instance_id": "{instance:id}",
            },
        },
        {
            "id": "test-webhook-pre-delete",
            "url": "http://localhost:8888/webhook",
            "method": "PUT",
            "triggers": ["pre-delete"],
            "headers": {
                "X-Trigger": "{trigger}",
                "X-Instance-ID": "{instance:id}",
            },
            "query_params": {
                "fqdn": "{instance:fqdn}",
                "ip": "{instance:ip_address}",
                "role": "{instance:meta:role}",
            },
        },
        {
            "id": "test-webhook-post-delete",
            "url": "http://localhost:8888/webhook",
            "method": "DELETE",
            "triggers": ["post-delete"],
            "headers": {
                "X-Trigger": "{trigger}",
                "X-Instance-ID": "{instance:id}",
            },
            "query_params": {
                "fqdn": "{instance:fqdn}",
                "ip": "{instance:ip_address}",
                "role": "{instance:meta:role}",
            },
        },
        {
            "id": "test-webhook-secrets",
            "url": "http://localhost:8888/webhook-secrets",
            "method": "POST",
            "triggers": ["post-create"],
            "username": "user-{instance:id}",
            "password": "{secret:test-secret-1}",
            "headers": {
                "X-Secret": "{secret:test-secret-1}",
            },
        },
    ]

    for webhook in webhooks_to_create:
        create_wh_response = client.post(
            url="/api/v2/webhooks",
            json=webhook,
            headers=headers,
        )
        if create_wh_response.status_code != 201:
            print(f"Failed to create webhook {webhook['id']}: {create_wh_response.text}")
        create_wh_response.raise_for_status()

    instances = [
        {
            "id": "test-instance-1",
            "payload": {
                "dns_indicator": "test-NUM",
                "ip_address": "192.168.1.50",
                "meta": {
                    "role": "database",
                },
            },
        },
        {
            "id": "test-instance-2",
            "payload": {
                "dns_indicator": "test-NUM",
                "ip_address": "192.168.1.60",
                "meta": {
                    "role": "frontend",
                },
            },
        },
    ]

    for instance in instances:
        create_inst_response = client.post(
            url=f"/api/v2/instances/{instance['id']}",
            json=instance["payload"],
            headers=headers,
        )
        if create_inst_response.status_code != 201:
            print(f"Failed to create instance {instance['id']}: {create_inst_response.text}")
        create_inst_response.raise_for_status()

    # Now create failing webhooks for negative tests
    failing_webhooks = [
        {
            "id": "test-webhook-fail-4xx",
            "url": "http://localhost:8888/webhook-fail-4xx",
            "method": "POST",
            "triggers": ["pre-create"],
            "fail_on_error": True,
        },
        {
            "id": "test-webhook-fail-5xx",
            "url": "http://localhost:8888/webhook-fail-5xx",
            "method": "POST",
            "triggers": ["pre-create"],
            "fail_on_error": True,
        },
    ]
    for webhook in failing_webhooks:
        client.post(
            url="/api/v2/webhooks",
            json=webhook,
            headers=headers,
        ).raise_for_status()

    create_inst_fail_400 = client.post(
        url="/api/v2/instances/test-instance-fail-400",
        json={
            "dns_indicator": "test-NUM",
            "ip_address": "192.168.1.70",
            "meta": {
                "role": "fail-400",
            },
        },
        headers=headers,
    )
    if create_inst_fail_400.status_code == 201:
        raise AssertionError("Instance creation should have failed due to 4xx webhook")

    # Delete 4xx fail webhook to test 5xx
    client.delete(
        url="/api/v2/webhooks/test-webhook-fail-4xx",
        headers=headers,
    ).raise_for_status()

    create_inst_fail_500 = client.post(
        url="/api/v2/instances/test-instance-fail-500",
        json={
            "dns_indicator": "test-NUM",
            "ip_address": "192.168.1.80",
            "meta": {
                "role": "fail-500",
            },
        },
        headers=headers,
    )
    if create_inst_fail_500.status_code == 201:
        raise AssertionError("Instance creation should have failed due to 5xx webhook")

    # Cleanup 5xx fail webhook
    client.delete(
        url="/api/v2/webhooks/test-webhook-fail-5xx",
        headers=headers,
    ).raise_for_status()

    time.sleep(2)

    for instance in instances:
        delete_inst_response = client.delete(
            url=f"/api/v2/instances/{instance['id']}",
            headers=headers,
        )
        delete_inst_response.raise_for_status()

    time.sleep(2)

    for wh_id in [
        "test-webhook-pre-create",
        "test-webhook-post-create",
        "test-webhook-pre-delete",
        "test-webhook-post-delete",
        "test-webhook-secrets",
    ]:
        delete_wh_response = client.delete(
            url=f"/api/v2/webhooks/{wh_id}",
            headers=headers,
        )
        delete_wh_response.raise_for_status()

    client.delete(
        url="/api/v2/secrets/test-secret-1",
        headers=headers,
    ).raise_for_status()

    delete_cred_response = client.delete(
        url=f"/api/v2/users/admin/credentials/{cred_id}",
        headers=headers,
    )
    delete_cred_response.raise_for_status()

    server.shutdown()

if __name__ == "__main__":
    run()
