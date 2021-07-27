import logging
import json
import os
import sys

import boto3
import botocore.exceptions
import requests

__version__ = '0.0.19'


def lambda_handler(event, context):
    cat_weazle_lambda = CatWeazleLambda(context=context, event=event)
    cat_weazle_lambda.run()


class CatWeazleLambda(object):
    def __init__(self, event, context):
        self._boto = None
        self._context = context
        self._event = event
        self._logger = logging.getLogger()
        self.log.setLevel(os.environ.get('CatWeazleLogLevel', logging.INFO))
        self._cw_endpoint = os.environ.get('CatWeazleEndPoint')
        self._cw_indicator_tag = os.environ.get('CatWeazleIndicatorTag')
        self._cw_indicator_tmpl = os.environ.get('CatWeazleIndicatorTemplate', None)
        self._cw_role_arn = os.environ.get('CatWeazleRoleARN')
        self._cw_secret = os.environ.get('CatWeazleSecret')
        self._cw_secret_id = os.environ.get('CatWeazleSecretID')
        self._cw_name_tag = os.environ.get('CatWeazleNameTag', 'Name')
        self._cw_name_tag_if_emtpy = os.environ.get('CatWeazleNameTagIfEmpty', True)
        self._cw_name_target_tag = os.environ.get('CatWeazleNameTargetTag', None)
        self._cw_role_session_name = os.environ.get('CatWeazleRoleSessionName', 'catweazle_session')
        self._cw_post_create_lambda = os.environ.get('CatWeazlePostCreateLambda', None)
        self._instance = None

    @property
    def boto(self):
        if self._boto:
            return self.boto
        account_id = self.event["account"]
        access_role_arn = self.cw_role_arn.format(account_id)
        self.log.info("Assuming role {0} for account {1}".format(access_role_arn, account_id))
        self._boto = self._get_session(access_role_arn)
        return self._boto

    @property
    def context(self):
        return self._context

    @property
    def cw_endpoint(self):
        return self._cw_endpoint

    @property
    def cw_indicator_tag(self):
        return self._cw_indicator_tag

    @property
    def cw_indicator_tmpl(self):
        return self._cw_indicator_tmpl

    @property
    def catweazle_post_create_lambda(self):
        return self._cw_post_create_lambda

    @property
    def cw_role_arn(self):
        return self._cw_role_arn

    @property
    def cw_role_session_name(self):
        return self._cw_role_session_name

    @property
    def cw_secret(self):
        return self._cw_secret

    @property
    def cw_secret_id(self):
        return self._cw_secret_id

    @property
    def cw_name_tag(self):
        return self._cw_name_tag

    @property
    def cw_name_tag_if_empty(self):
        return self._cw_name_tag_if_emtpy

    @property
    def cw_name_target_tag(self):
        return self._cw_name_target_tag

    @property
    def ec2_id(self):
        return self.event['detail']['instance-id']

    @property
    def event(self):
        return self._event

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
            RoleArn=role, RoleSessionName=self.cw_role_session_name, DurationSeconds=900
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

    def post_create_lambda(self):
        self.log.info("calling post create lambda functions")
        if not self._cw_post_create_lambda:
            self.log.info("calling post create lambda functions, done")
            return
        self.log.info("getting session in this account")
        session = boto3.Session()
        aws_lambda = session.client('lambda')
        self.log.info("getting session in this account, done")
        try:
            for _function in self._cw_post_create_lambda.split(','):
                self.log.info("calling post create lambda function {0}".format(_function))
                response = aws_lambda.invoke(
                    FunctionName=_function,
                    InvocationType='Event',
                    Payload=json.dumps(self.event)
                )
                self.log.info(response)
                self.log.info("calling post create lambda function {0}, done".format(_function))
        except Exception as err:
            self.log.fatal(err)
        self.log.info("calling post create lambda functions, done")

    def instance_create(self):
        self.log.info("registering new instance")

        self.log.info("fetching instance details")
        payload = dict()
        payload['ip_address'] = self.instance.private_ip_address
        payload['dns_indicator'] = self.get_dns_indicator()
        self.log.info("fetching instance details, done")

        try:
            self.log.info("registering instance in catweazle")
            url = "{0}/api/v1/instances/{1}".format(self.cw_endpoint, self.ec2_id)
            headers = {
                'X-ID': self.cw_secret_id,
                'X-SECRET': self.cw_secret
            }
            resp = requests.post(url, headers=headers, json={'data': payload})
            self.log.info("status: {0}".format(resp.status_code))
            if resp.status_code != 201:
                self.log.error("request error: {0}".format(resp.text))
                sys.exit(0)
            fqdn = resp.json()['data']['fqdn']
            fqdn_tag_name = self.get_fqdn_tag_name()
            self.set_ec2_tag(fqdn=fqdn, fqdn_tag_name=fqdn_tag_name)
            if not self.get_tag('Name') and self.cw_name_tag_if_empty:
                self.log.info("Also setting Name tag, since it is currently empty.")
                self.set_ec2_tag(fqdn=fqdn, fqdn_tag_name='Name')
            self.log.info("registering instance in catweazle, done")
        except requests.exceptions.RequestException as err:
            self.log.error("could not create instance {0}".format(err))
        self.post_create_lambda()
        self.log.info("registering new instance, done")

    def set_ec2_tag(self, fqdn, fqdn_tag_name):
        try:
            self.log.info("setting {0} tag of instance to {1}".format(
                fqdn_tag_name, fqdn))
            self.instance.create_tags(Tags=[{'Key': fqdn_tag_name, 'Value': fqdn}])
            self.log.info("setting {0} tag of instance to {1}, done".format(
                fqdn_tag_name, fqdn))
        except botocore.exceptions.ClientError as err:
            self.log.error("setting {0} tag failed: {1}".format(
                fqdn_tag_name, err))

    def get_dns_indicator(self):
        self.log.info("fetching instance dns indicator")
        dns_indicator = self.get_tag(self.cw_indicator_tag)
        if not dns_indicator:
            self.log.error("instance is missing the name indicator tag, exit")
            sys.exit(0)
        if dns_indicator.startswith('INSTANCEID'):
            dns_indicator = dns_indicator.replace('INSTANCEID', self.ec2_id)
        if self.cw_indicator_tmpl:
            dns_indicator = self.cw_indicator_tmpl.format(dns_indicator)
        self.log.info("using indicator {0}".format(dns_indicator))
        self.log.info("fetching instance dns indicator, done")
        return dns_indicator

    def get_fqdn_tag_name(self):
        fqdn_tag_name = self.cw_name_tag
        self.log.info("setting Name tag to default {0}".format(fqdn_tag_name))
        if self.cw_name_target_tag:
            name_target_tag = self.get_tag(self.cw_name_target_tag)
            if name_target_tag:
                self.log.info("overriding Name tag to {0}".format(name_target_tag))
                return name_target_tag
        return fqdn_tag_name

    def get_tag(self, tag_name):
        for tag in self.instance.tags:
            if tag['Key'] == tag_name:
                return tag['Value']

    def instance_delete(self):
        self.log.info("deleting instance")
        url = "{0}/api/v1/instances/{1}".format(self.cw_endpoint, self.ec2_id)
        headers = {
            'X-ID': self.cw_secret_id,
            'X-SECRET': self.cw_secret
        }
        try:
            self.log.info("deleting instance in catweazle")
            resp = requests.delete(url, headers=headers)
            self.log.info("status: {0}".format(resp.status_code))
            if resp.status_code != 200:
                self.log.error("request error: {0}".format(resp.text))
            self.log.info("deleting instance in catweazle, done")
        except requests.exceptions.RequestException as err:
            self.log.error("could not remove instance {0}".format(err))
        self.log.info("deleting instance, done")

    def run(self):
        self.log.info("start working on {0}".format(self.event['id']))
        self.log.info("script version: {0}".format(__version__))
        self.log.info("event payload: {0}".format(self.event))

        if self.event['source'] != 'aws.ec2':
            self.log.fatal("got event from unexpected event source: {0}".format(self.event))
            sys.exit(0)

        state = self.event['detail']['state']

        self.log.info("got aws.ec2 {0} event for instance {1}".format(state, self.ec2_id))

        if state == 'pending':
            self.instance_create()
        elif state == 'shutting-down':
            self.instance_delete()
        elif state == 'terminated':
            self.instance_delete()
        else:
            self.log.fatal("got unexpected event state {0}".format(state))
            sys.exit(0)

        self.log.info("finished working on {0}".format(self.event['id']))
