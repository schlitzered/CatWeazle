import ipaddress

import aioboto3

from botocore.exceptions import ClientError

from catweazle.applog import AppLogging

# exception if record not found, and trying to delete
# botocore.errorfactory.InvalidChangeBatch:


class AWSRoute53(object):
    def __init__(
            self, name, dry_run,
            dns_arpa_enable, dns_arpa_zones,
            dns_forward_enable, dns_forward_zone,
    ):
        self._dns_arpa_enable = dns_arpa_enable
        self._dns_arpa_zones = dict()
        for subnet in dns_arpa_zones.split(' '):
            subnet, subnet_id = subnet.rsplit(':')
            self._dns_arpa_zones[ipaddress.ip_network(subnet)] = subnet_id
        self._dns_forward_enable = dns_forward_enable
        self._dns_forward_zone = dns_forward_zone
        self._name = name
        self._dry_run = dry_run
        self.log = AppLogging()

    @property
    def dns_arpa_enable(self):
        return self._dns_forward_enable

    @property
    def dns_arpa_zones(self):
        return self._dns_arpa_zones

    @property
    def dns_forward_enable(self):
        return self._dns_forward_enable

    @property
    def dns_forward_zone(self):
        return self._dns_forward_zone

    @property
    def dry_run(self):
        return self._dry_run

    @property
    def name(self):
        return self._name

    def arpa_responsible(self, ip_address):
        for subnet, subnet_id in self.dns_arpa_zones.items():
            if ip_address in subnet:
                self.log.info("{0}:aws: responsible DNS zone {1} with id {2}".format(self.name, subnet, subnet_id))
                return subnet_id

    async def create(self, fqdn, ip_address):
        self.log.info("{0}:aws: creating DNS Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        await self.create_arpa(fqdn=fqdn, ip_address=ip_address)
        await self.create_forward(fqdn=fqdn, ip_address=ip_address)
        self.log.info("{0}:aws: creating DNS Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

    async def create_forward(self, fqdn, ip_address):
        if not self.dns_forward_enable:
            self.log.info("{0}:aws: forward DNS is disabled".format(self.name))
            return
        if self.dry_run:
            return
        async with aioboto3.client('route53') as client:
            try:
                await client.change_resource_record_sets(
                    HostedZoneId=self.dns_forward_zone,
                    ChangeBatch={
                        "Comment": "CatWeazle: add {0} in A {1}".format(fqdn, ip_address),
                        "Changes": [
                            {
                                "Action": "UPSERT",
                                "ResourceRecordSet": {
                                    "Name": fqdn,
                                    "Type": "A",
                                    "TTL": 300,
                                    "ResourceRecords": [{"Value": ip_address}]
                                }
                            }]
                    })
            except ClientError:
                pass

    async def create_arpa(self, fqdn, ip_address):
        if not self.dns_arpa_enable:
            self.log.info("{0}:aws: reverse DNS is disabled".format(self.name))
            return
        ip_addr = ipaddress.IPv4Address(ip_address)
        subnet_id = self.arpa_responsible(ip_address=ip_addr)
        if not subnet_id:
            return
        if self.dry_run:
            return
        async with aioboto3.client('route53') as client:
            try:
                await client.change_resource_record_sets(
                    HostedZoneId=subnet_id,
                    ChangeBatch={
                        "Comment": "CatWeazle: add {0} in PTR {1}".format(fqdn, ip_address),
                        "Changes": [
                            {
                                "Action": "UPSERT",
                                "ResourceRecordSet": {
                                    "Name": ip_addr.reverse_pointer,
                                    "Type": "PTR",
                                    "TTL": 300,
                                    "ResourceRecords": [{"Value": fqdn}]
                                }
                            }]
                    })
            except ClientError:
                pass

    async def delete(self, fqdn, ip_address):
        self.log.info("{0}:aws: deleting DNS Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        await self.delete_arpa(fqdn=fqdn, ip_address=ip_address)
        await self.delete_forward(fqdn=fqdn, ip_address=ip_address)
        self.log.info("{0}:aws: deleting DNS Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

    async def delete_forward(self, fqdn, ip_address):
        if not self.dns_arpa_enable:
            self.log.info("{0}:aws: forward DNS is disabled".format(self.name))
            return
        if self.dry_run:
            return
        async with aioboto3.client('route53') as client:
            try:
                await client.change_resource_record_sets(
                    HostedZoneId=self.dns_forward_zone,
                    ChangeBatch={
                        "Comment": "CatWeazle: remove {0} in A {1}".format(fqdn, ip_address),
                        "Changes": [
                            {
                                "Action": "DELETE",
                                "ResourceRecordSet": {
                                    "Name": fqdn,
                                    "Type": "A",
                                    "TTL": 300,
                                    "ResourceRecords": [{"Value": ip_address}]
                                }
                            }]
                    })
            except ClientError:
                pass

    async def delete_arpa(self, fqdn, ip_address):
        if not self.dns_arpa_enable:
            self.log.info("{0}:aws: reverse DNS is disabled".format(self.name))
            return
        ip_addr = ipaddress.IPv4Address(ip_address)
        subnet_id = self.arpa_responsible(ip_address=ip_addr)
        if not subnet_id:
            return
        if self.dry_run:
            return
        async with aioboto3.client('route53') as client:
            try:
                await client.change_resource_record_sets(
                    HostedZoneId=subnet_id,
                    ChangeBatch={
                        "Comment": "CatWeazle: remove {0} in PTR {1}".format(fqdn, ip_address),
                        "Changes": [
                            {
                                "Action": "DELETE",
                                "ResourceRecordSet": {
                                    "Name": ip_addr.reverse_pointer,
                                    "Type": "PTR",
                                    "TTL": 300,
                                    "ResourceRecords": [{"Value": fqdn}]
                                }
                            }]
                    })
            except ClientError:
                pass
