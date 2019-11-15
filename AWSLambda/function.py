import logging
import os
import sys

import boto3
import botocore.exceptions
import requests


def lambda_handler(event, context):
    cat_weazle_lambda = CatWeazleLambda(context=context, event=event)
    cat_weazle_lambda.run()


class CatWeazleLambda(object):
    def __init__(self, event, context):
        self._boto = None
        self._context = context
        self._ec2_id = None
        self._event = event
        self._logger = logging.getLogger()
        self.log.setLevel(os.environ.get('CatWeazleLogLevel', logging.INFO))
        self._cw_endpoint = os.environ.get('CatWeazleEndPoint')
        self._cw_indicator_tag = os.environ.get('CatWeazleIndicatorTag')
        self._cw_role_arn = os.environ.get('CatWeazleRoleARN')
        self._cw_secret = os.environ.get('CatWeazleSecret')
        self._cw_secret_id = os.environ.get('CatWeazleSecretID')
        self._cw_role_session_name = os.environ.get('CatWeazleRoleSessionName', 'catweazle_session')

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
    def cw_role_arn(self):
        return self._cw_role_arn

    @property
    def cw_secret(self):
        return self._cw_secret

    @property
    def cw_secret_id(self):
        return self._cw_secret_id

    @property
    def ec2_id(self):
        return self._ec2_id

    @ec2_id.setter
    def ec2_id(self, value):
        self._ec2_id = value

    @property
    def event(self):
        return self._event

    @property
    def log(self):
        return self._logger

    @staticmethod
    def _get_role_credentials(role):
        session = boto3.Session()
        sts = session.client("sts")
        role = sts.assume_role(
            RoleArn=role, RoleSessionName="sts_lambda_session", DurationSeconds=900
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

    def instance_create(self):
        self.log.info("registering new instance")
        self.log.info("fetching instance details")
        ec2 = self.boto.resource("ec2")
        instance = ec2.Instance(self.ec2_id)

        url = "{0}/api/v1/instances/{1}".format(self.cw_endpoint, self.ec2_id)
        headers = {
            'X-ID': self.cw_secret_id,
            'X-SECRET': self.cw_secret
        }
        self.log.info("fetching instance ip")
        payload = {
            'ip_address': instance.private_ip_address
        }
        self.log.info("fetching instance ip, done")

        self.log.info("fetching instance dns indicator")
        for tag in instance.tags:
            if tag['Key'] == self.cw_indicator_tag:
                payload['dns_indicator'] = tag['Value']
                break
        if 'dns_indicator' not in payload:
            self.log.error("instance is missing the name indicator tag, exit")
            sys.exit(1)
        if payload['dns_indicator'].startswith('INSTANCEID'):
            payload['dns_indicator'].replace('INSTANCEID', self.ec2_id)
            self.log.info("setting indicator based on instance-id: {0}".format(payload['dns_indicator']))
        self.log.info("fetching instance dns indicator, done")
        self.log.info("fetching instance details, done")
        fqdn = None
        try:
            self.log.info("registering instance in catweazle")
            resp = requests.post(url, headers=headers, json={'data': payload})
            self.log.info("status: {0}".format(resp.status_code))
            if resp.status_code != 201:
                self.log.error("request error: {0}".format(resp.text))
            fqdn = resp.json()['data']['fqdn']
            self.log.info("registering instance in catweazle, done")
        except requests.exceptions.RequestException as err:
            self.log.error("could not create instance {0}".format(err))
        if fqdn:
            try:
                self.log.info("setting Name tag of instance to {0}".format(fqdn))
                instance.create_tags(Tags=[{'Key': 'Name', 'Value': fqdn}])
                self.log.info("setting Name tag of instance to {0}, done".format(fqdn))
            except botocore.exceptions.ClientError as err:
                self.log.error("setting Name tag failed: {0}".format(err))
        self.log.info("registering new instance, done")

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
            if resp.status_code != '200':
                self.log.error("request error: {0}".format(resp.text))
            self.log.info("deleting instance in catweazle, done")
        except requests.exceptions.RequestException as err:
            self.log.error("could not remove instance {0}".format(err))
        self.log.info("deleting instance, done")

    def run(self):
        self.log.info("start working on {0}".format(self.event['id']))
        self.log.info("event payload: {0}".format(self.event))

        if self.event['source'] != 'aws.ec2':
            self.log.fatal("got event from unexpected event source: {0}".format(self.event))
            sys.exit(1)

        self.ec2_id = self.event['detail']['instance-id']
        state = self.event['detail']['state']

        self.log.info("got aws.ec2 {0} event for instance {1}".format(state, self.ec2_id))

        if state == 'pending':
            self.instance_create()
        elif state == 'terminated':
            self.instance_delete()
        else:
            self.log.fatal("got unexpected event state {0}".format(state))
            sys.exit(1)

        self.log.info("finished working on {0}".format(self.event['id']))
