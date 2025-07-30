import logging
import json
import os
import sys
import time

import boto3
import botocore.exceptions
import httpx

__version__ = "2.0.0"


def lambda_handler(event, context):
    cat_weazle_lambda = CatWeazleLambda(context=context, event=event)
    cat_weazle_lambda.run()


class CatWeazleLambda(object):
    def __init__(self, event, context):
        self._boto = None
        self.context = context
        self.event = event
        self._logger = logging.getLogger()
        self.log.setLevel(os.environ.get("CatWeazleLogLevel", logging.INFO))
        self._api_version = None
        self.cw_endpoint = os.environ.get("CatWeazleEndPoint")
        self.cw_indicator_tag = os.environ.get("CatWeazleIndicatorTag")
        self.cw_indicator_tmpl = os.environ.get("CatWeazleIndicatorTemplate", None)
        self.cw_role_arn = os.environ.get("CatWeazleRoleARN")
        self.cw_secret = os.environ.get("CatWeazleSecret")
        self.cw_secret_id = os.environ.get("CatWeazleSecretID")
        self.cw_name_tag = os.environ.get("CatWeazleNameTag", "Name")
        self.cw_name_tag_if_empty = os.environ.get("CatWeazleNameTagIfEmpty", True)
        self.cw_name_target_tag = os.environ.get("CatWeazleNameTargetTag", None)
        self.cw_role_session_name = os.environ.get(
            "CatWeazleRoleSessionName", "catweazle_session"
        )
        self.cw_post_create_lambda = os.environ.get("CatWeazlePostCreateLambda", None)
        self._instance = None
        self._validate_configuration()

    def _validate_configuration(self):
        required_vars = {
            "CatWeazleEndPoint": self.cw_endpoint,
            "CatWeazleSecret": self.cw_secret,
            "CatWeazleSecretID": self.cw_secret_id,
            "CatWeazleRoleARN": self.cw_role_arn,
            "CatWeazleIndicatorTag": self.cw_indicator_tag,
        }

        missing = [name for name, value in required_vars.items() if not value]
        if missing:
            self.log.fatal(
                f"Missing required environment variables: {', '.join(missing)}"
            )
            sys.exit(0)

    @property
    def boto(self):
        if not self._boto:
            access_role_arn = self.cw_role_arn.format(self.account_id)
            self.log.info(self._fmt_log_msg(f"Assuming role {access_role_arn}"))
            self._boto = self._get_session(access_role_arn)
        return self._boto

    @property
    def api_version(self):
        if not self._api_version:
            try:
                data = self.catweazle_api(
                    method="GET",
                    endpoint="version",
                )
                self._api_version = data["version"]
            except httpx.HTTPError as err:
                self.log.warning(
                    self._fmt_log_msg(f"Could not get API version: {err}, assuming v1")
                )
                self._api_version = "v1"
        return self._api_version

    @property
    def ec2_id(self):
        return self.event["detail"]["instance-id"]

    @property
    def account_id(self):
        return self.event["account"]

    @property
    def instance(self):
        if not self._instance:
            ec2 = self.boto.resource("ec2")
            self._instance = ec2.Instance(self.ec2_id)
        return self._instance

    @property
    def log(self):
        return self._logger

    def _get_role_credentials(self, role):
        session = boto3.Session()
        sts = session.client("sts")
        role = sts.assume_role(
            RoleArn=role,
            RoleSessionName=self.cw_role_session_name,
            DurationSeconds=900,
        )
        access_key = role["Credentials"]["AccessKeyId"]
        secret_key = role["Credentials"]["SecretAccessKey"]
        session_token = role["Credentials"]["SessionToken"]
        return access_key, secret_key, session_token

    def _get_session(self, role):
        cred = self._get_role_credentials(role)
        session = boto3.Session(
            aws_access_key_id=cred[0],
            aws_secret_access_key=cred[1],
            aws_session_token=cred[2],
        )
        return session

    def catweazle_api(self, method, endpoint, body=None, api_version=None) -> dict:
        url = f"{self.cw_endpoint}/api/{endpoint}"
        headers = {
            "X-ID": self.cw_secret_id,
            "X-SECRET-ID": self.cw_secret_id,
            "X-SECRET": self.cw_secret,
        }
        if api_version == "v1" and body:
            body = {"data": body}
        try:
            self.log.info(self._fmt_log_msg(f"request: {method} {url} {body}"))
            with httpx.Client(timeout=30) as client:
                resp = client.request(method, url, headers=headers, json=body)
                resp.raise_for_status()
                if api_version == "v1" and method != "DELETE":
                    return resp.json()["data"]
                return resp.json()
        except httpx.HTTPError as err:
            self.log.error(self._fmt_log_msg(f"request error: {err}"))
            raise err

    def post_create_lambda(self):
        self.log.info(self._fmt_log_msg("calling post create lambda functions"))
        if not self.cw_post_create_lambda:
            self.log.info(
                self._fmt_log_msg("calling post create lambda functions, done")
            )
            return
        self.log.info(self._fmt_log_msg("getting session in this account"))
        session = boto3.Session()
        aws_lambda = session.client("lambda")
        self.log.info(self._fmt_log_msg("getting session in this account, done"))
        for function in self.cw_post_create_lambda.split(","):
            try:
                self.log.info(
                    self._fmt_log_msg(f"calling post create lambda function {function}")
                )
                response = aws_lambda.invoke(
                    FunctionName=function,
                    InvocationType="Event",
                    Payload=json.dumps(self.event),
                )
                self.log.info(
                    self._fmt_log_msg(
                        f"calling post create lambda function {function}, done, response: {response}"
                    )
                )
            except Exception as err:
                self.log.info(
                    self._fmt_log_msg(
                        f"calling post create lambda function {function}, failed, error: {err}"
                    )
                )
        self.log.info(self._fmt_log_msg("calling post create lambda functions, done"))

    def _add_body_meta(self, body):
        if self.api_version == "v1":
            return
        body["meta"] = dict()
        body["meta"]["account_id"] = self.account_id
        body["meta"]["instance_id"] = self.ec2_id
        body["meta"]["instance_state"] = self.event["detail"]["state"]

    def instance_create(self):
        self.log.info(self._fmt_log_msg("create instance"))
        body = dict()
        body["ip_address"] = self.instance.private_ip_address
        body["dns_indicator"] = self.get_dns_indicator()
        self._add_body_meta(body)
        try:
            path = f"{self.api_version}/instances/{self.ec2_id}"
            resp = self.catweazle_api(
                method="POST", endpoint=path, body=body, api_version=self.api_version
            )
        except httpx.HTTPError as err:
            self.log.error(self._fmt_log_msg(f"create instance failed {err}"))
            sys.exit(1)
        fqdn = resp["fqdn"]
        fqdn_tag_name = self.get_fqdn_tag_name()
        self.set_ec2_tag(fqdn=fqdn, fqdn_tag_name=fqdn_tag_name)
        if not self.get_tag("Name") and self.cw_name_tag_if_empty:
            self.log.info(
                self._fmt_log_msg("setting Name tag, since it is currently empty.")
            )
            self.set_ec2_tag(fqdn=fqdn, fqdn_tag_name="Name")
        self.post_create_lambda()
        self.log.info(self._fmt_log_msg("create instance, done"))

    def instance_delete(self):
        self.log.info(self._fmt_log_msg("deleting instance"))
        try:
            path = f"{self.api_version}/instances/{self.ec2_id}"
            self.catweazle_api(
                method="DELETE", endpoint=path, api_version=self.api_version
            )
        except httpx.HTTPError as err:
            self.log.error(self._fmt_log_msg(f"could not delete instance {err}"))
            sys.exit(0)
        self.log.info(self._fmt_log_msg("deleting instance, done"))

    def instance_update(self):
        if self.api_version == "v1":
            return
        self.log.info(self._fmt_log_msg("update instance"))
        body = dict()
        self._add_body_meta(body)
        try:
            path = f"{self.api_version}/instances/{self.ec2_id}"
            self.catweazle_api(
                method="PUT", endpoint=path, body=body, api_version=self.api_version
            )
        except httpx.HTTPError as err:
            self.log.error(self._fmt_log_msg(f"could not update instance {err}"))
            sys.exit(0)
        self.log.info(self._fmt_log_msg("update instance, done"))

    def set_ec2_tag(self, fqdn, fqdn_tag_name):
        try:
            self.log.info(
                self._fmt_log_msg(f"setting {fqdn_tag_name} tag of instance to {fqdn}")
            )
            self.instance.create_tags(Tags=[{"Key": fqdn_tag_name, "Value": fqdn}])
            self.log.info(
                self._fmt_log_msg(
                    f"setting {fqdn_tag_name} tag of instance to {fqdn}, done"
                )
            )
        except botocore.exceptions.ClientError as err:
            self.log.error(
                self._fmt_log_msg(f"setting {fqdn_tag_name} tag failed {err}")
            )

    def get_dns_indicator(self):
        self.log.info(self._fmt_log_msg("fetching instance dns indicator"))
        dns_indicator = self.get_tag(self.cw_indicator_tag, retry=10)
        if not dns_indicator:
            self.log.error(
                self._fmt_log_msg("instance is missing the name indicator tag, exit")
            )
            sys.exit(0)
        if dns_indicator.startswith("INSTANCEID"):
            dns_indicator = dns_indicator.replace("INSTANCEID", self.ec2_id)
        if self.cw_indicator_tmpl:
            dns_indicator = self.cw_indicator_tmpl.format(dns_indicator)
        self.log.info(self._fmt_log_msg(f"using indicator {dns_indicator}"))
        self.log.info(self._fmt_log_msg("fetching instance dns indicator, done"))
        return dns_indicator

    def get_fqdn_tag_name(self):
        fqdn_tag_name = self.cw_name_tag
        self.log.info(self._fmt_log_msg(f"setting Name tag to default {fqdn_tag_name}"))
        if self.cw_name_target_tag:
            name_target_tag = self.get_tag(self.cw_name_target_tag)
            if name_target_tag:
                self.log.info(
                    self._fmt_log_msg(f"overriding Name tag to {name_target_tag}")
                )
                return name_target_tag
        return fqdn_tag_name

    def get_tag(self, tag_name, retry=None):
        if not retry:
            return self._get_tag(tag_name)
        while retry > 0:
            result = self._get_tag(tag_name)
            if result:
                return result
            self.instance.reload()
            retry -= 1
            time.sleep(2)
        return None

    def _get_tag(self, tag_name):
        if not self.instance.tags:
            return None
        for tag in self.instance.tags:
            if tag["Key"] == tag_name:
                return tag["Value"]
        return None

    def _fmt_log_msg(self, msg):
        return f"{self.account_id}/{self.ec2_id}: {msg}"

    def run(self):
        self.log.info(
            f"script version: {__version__}, start working on {self.event['id']}, event payload: {self.event}"
        )

        if self.event["source"] != "aws.ec2":
            self.log.fatal(f"got event from unexpected event source: {self.event}")
            sys.exit(0)

        state = self.event["detail"]["state"]

        self.log.info(self._fmt_log_msg(f"got aws.ec2 {state} event"))

        if state == "pending":
            self.instance_create()
        elif state == "shutting-down":
            self.instance_update()
            self.instance_delete()
        elif state == "terminated":
            self.instance_update()
            self.instance_delete()
        else:
            self.instance_update()

        self.log.info(self._fmt_log_msg(f"finished working on {self.event['id']}"))
