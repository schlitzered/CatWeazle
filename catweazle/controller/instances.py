__author__ = 'schlitzer'
import jsonschema
import jsonschema.exceptions
import re

from aiohttp.web import json_response

from catweazle.applog import AppLogging
from catweazle.schemes import INSTANCES_CREATE
from catweazle.errors import BackEndError
from catweazle.errors import BaseError
from catweazle.errors import InvalidName
from catweazle.errors import ForemanConnError
from catweazle.errors import ModelError
from catweazle.errors import ResourceNotFound


class Instances:
    def __init__(self, aa, aws_route53, foreman, foreman_realm, instances, indicator_regex):
        self._aa = aa
        self._aws_route53 = aws_route53
        self._foreman = foreman
        self._foreman_realm = foreman_realm
        self._instances = instances
        self._indicator_regex = re.compile(indicator_regex)
        self.log = AppLogging()

    @property
    def aa(self):
        return self._aa

    @property
    def aws_route53(self):
        return self._aws_route53

    @property
    def foreman(self):
        return self._foreman

    @property
    def foreman_realm(self):
        return self._foreman_realm

    @property
    def indicator_regex(self):
        return self._indicator_regex

    @property
    def instances(self):
        return self._instances

    async def delete(self, request):
        instance = request.match_info['instance']
        await self.aa.require(request, 'INSTANCE:DELETE')
        _instance = await self.instances.get(instance)
        for foreman in self.foreman:
            try:
                await foreman.delete_dns(
                    fqdn=_instance['data']['fqdn'],
                    ip_address=_instance['data']['ip_address']
                )
            except ForemanConnError as err:
                self.log.error(err.msg)
        for aws in self.aws_route53:
            try:
                await aws.delete(
                    fqdn=_instance['data']['fqdn'],
                    ip_address=_instance['data']['ip_address']
                )
            except ForemanConnError as err:
                self.log.error(err.msg)
        try:
            if self.foreman_realm:
                await self.foreman_realm.delete_realm(
                    fqdn=_instance['data']['fqdn'],
                )
        except ForemanConnError as err:
            self.log.error(err.msg)
        result = await self.instances.delete(instance)
        return json_response(result)

    async def get(self, request):
        instance = request.match_info['instance']
        try:
            await self.aa.require(request, instance)
        except ModelError as err:
            try:
                _result = await self.instances.get(instance, 'id,ip_address')
                self.log.info("remote ip is: {0}".format(request.remote))
                self.log.info(request.headers)
                if request.remote != _result['data']['ip_address']:
                    raise err
            except ResourceNotFound:
                raise err

        fields = request.query.get('fields', None)
        result = await self.instances.get(instance, fields)
        return json_response(result)

    async def post(self, request):
        instance = request.match_info['instance']
        await self.aa.require(request, 'INSTANCE:POST')
        payload = await request.json()
        jsonschema.validate(payload, INSTANCES_CREATE, format_checker=jsonschema.draft4_format_checker)
        payload = payload.get('data')
        if not self.indicator_regex.match(instance):
            raise InvalidName('{0}'.format(instance))
        result = await self.instances.create(instance, payload)
        try:
            for foreman in self.foreman:
                await foreman.create_dns(
                    fqdn=result['data']['fqdn'],
                    ip_address=result['data']['ip_address']
                )
            for aws in self.aws_route53:
                await aws.create(
                    fqdn=result['data']['fqdn'],
                    ip_address=result['data']['ip_address']
                )
            if self.foreman_realm:
                ipa_otp = await self.foreman_realm.create_realm(
                    fqdn=result['data']['fqdn'],
                )
                result = await self.instances.set_ipa_otp(instance, ipa_otp)
        except BaseError as err:
            self.log.error("something went wrong, rolling back")
            self.log.error(err.msg)
            await self.delete(request)
            raise BackEndError('Could not create instance in backend, please check logs')
        return json_response(result, status=201)

    async def search(self, request):
        result = await self.instances.search(
            instances=request.query.get('instances', None),
            dns_indicator=request.query.get('dns_indicator', None),
            ip_address=request.query.get('ip_address', None),
            fqdn=request.query.get('fqdn', None),
            fields=request.query.get('fields', None),
            sort=request.query.get('sort', None),
            page=request.query.get('page', None),
            limit=request.query.get('limit', None),
        )
        return json_response(result)
