import aiohttp
import ssl

import ipaddress

from catweazle.applog import AppLogging
from catweazle.errors import ForemanConnError


class ForemanProxy(object):
    def __init__(
            self, name, dry_run, url, ssl_key, ssl_crt,
            dns_arpa_enable, dns_arpa_zones,
            dns_forward_enable,
            realm
    ):
        self._dns_arpa_enable = dns_arpa_enable
        self._dns_arpa_zones = set()
        for subnet in dns_arpa_zones.split(' '):
            if subnet:
                self._dns_arpa_zones.add(ipaddress.ip_network(subnet))
        self._dns_forward_enable = dns_forward_enable
        self._dry_run = dry_run
        self._name = name
        self._realm = realm
        self._ssl_crt = ssl_crt
        self._ssl_key = ssl_key
        self._url = url
        self.log = AppLogging()

    @property
    def dns_arpa_enable(self):
        return self._dns_arpa_enable

    @property
    def dns_arpa_zones(self):
        return self._dns_arpa_zones

    @property
    def dns_forward_enable(self):
        return self._dns_forward_enable

    @property
    def dry_run(self):
        return self._dry_run

    @property
    def name(self):
        return self._name

    @property
    def realm(self):
        return self._realm

    @property
    def ssl_crt(self):
        return self._ssl_crt

    @property
    def ssl_key(self):
        return self._ssl_key

    @property
    def url(self):
        return self._url

    async def request_delete(self, url):
        if self.dry_run:
            return
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(certfile=self.ssl_crt, keyfile=self.ssl_key)
        async with aiohttp.ClientSession() as session:
            async with await session.delete(url, ssl=context) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ForemanConnError(text)

    async def request_post(self, url, data):
        if self.dry_run:
            return
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_cert_chain(certfile=self.ssl_crt, keyfile=self.ssl_key)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, ssl=context) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ForemanConnError(text)
                try:
                    data = await resp.json()
                    return data
                except aiohttp.ClientError:
                    pass

    def arpa_responsible(self, ip_address):
        for zone in self.dns_arpa_zones:
            if ip_address in zone:
                return True

    async def create_dns(self, fqdn, ip_address):
        await self.create_arpa_dns(fqdn=fqdn, ip_address=ip_address)
        await self.create_forward_dns(fqdn=fqdn, ip_address=ip_address)

    async def create_arpa_dns(self, fqdn, ip_address):
        self.log.info("{0}:foreman: creating DNS PTR Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        if not self.dns_arpa_enable:
            self.log.info("{0}:foreman: reverse DNS is disabled".format(self.name))
            return
        url = "{0}{1}".format(self.url, '/dns/')
        body_ptr = aiohttp.FormData()
        ip_addr = ipaddress.IPv4Address(ip_address)
        if self.arpa_responsible(ip_address=ip_addr):
            body_ptr.add_field('fqdn', fqdn)
            body_ptr.add_field('value', ip_addr.reverse_pointer)
            body_ptr.add_field('type', 'PTR')
            await self.request_post(url, body_ptr)
        self.log.info("{0}:foreman: creating DNS PTR Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

    async def create_forward_dns(self, fqdn, ip_address):
        self.log.info("{0}:foreman: creating DNS A Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        if not self.dns_forward_enable:
            self.log.info("{0}:foreman: forward DNS is disabled".format(self.name))
            return
        url = "{0}{1}".format(self.url, '/dns/')
        body_a = aiohttp.FormData()
        body_a.add_field('fqdn', fqdn)
        body_a.add_field('value', ip_address)
        body_a.add_field('type', 'A')
        self.log.info("{0}:foreman: creating DNS A Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

        await self.request_post(url, body_a)

    async def delete_dns(self, fqdn, ip_address):
        await self.delete_arpa_dns(fqdn=fqdn, ip_address=ip_address)
        await self.delete_forward_dns(fqdn=fqdn, ip_address=ip_address)

    async def delete_arpa_dns(self, ip_address, fqdn):
        self.log.info("{0}:foreman: deleting DNS PTR Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        if not self.dns_arpa_enable:
            self.log.info("{0}:foreman: reverse DNS is disabled".format(self.name))
            return
        ip_addr = ipaddress.IPv4Address(ip_address)
        if self.arpa_responsible(ip_address=ip_addr):
            url_ptr = "{0}{1}{2}/PTR".format(self.url, '/dns/', ip_addr.reverse_pointer)
            await self.request_delete(url_ptr)
        self.log.info("{0}:foreman: deleting DNS PTR Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

    async def delete_forward_dns(self, ip_address, fqdn):
        self.log.info("{0}:foreman: deleting DNS A Records for {1} with ip {2}".format(self.name, fqdn, ip_address))
        if not self.dns_forward_enable:
            self.log.info("{0}:foreman: forward DNS is disabled".format(self.name))
            return
        url_a = "{0}{1}{2}/A".format(self.url, '/dns/', fqdn)
        await self.request_delete(url_a)
        self.log.info("{0}:foreman: deleting DNS A Records for {1} with ip {2}, done".format(self.name, fqdn, ip_address))

    async def create_realm(self, fqdn):
        self.log.info("{0}:foreman: creating realm entry for {1}".format(self.name, fqdn))
        if self.dry_run:
            return 'dry_run_dummy_pw'
        url = "{0}{1}{2}".format(self.url, '/realm/', self.realm)
        body_a = aiohttp.FormData()
        body_a.add_field('hostname', fqdn)

        data = await self.request_post(url, body_a)
        self.log.info("{0}:foreman: creating realm entry for {1}, done".format(self.name, fqdn))
        return data['randompassword']

    async def delete_realm(self, fqdn):
        self.log.info("{0}:foreman: deleting realm entry for {1}".format(self.name, fqdn))
        url = "{0}{1}{2}/{3}".format(self.url, '/realm/', self.realm, fqdn)
        self.log.info("{0}:foreman: deleting realm entry for {1}, done".format(self.name, fqdn))
        await self.request_delete(url)


#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: proto = await self._create_connection(req, traces, timeout)
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: File "/opt/catweazle/lib64/python3.6/site-packages/aiohttp/connector.py", line 859, in _create_connection
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: req, traces, timeout)
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: File "/opt/catweazle/lib64/python3.6/site-packages/aiohttp/connector.py", line 1004, in _create_direct_connection
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: raise last_exc
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: File "/opt/catweazle/lib64/python3.6/site-packages/aiohttp/connector.py", line 986, in _create_direct_connection
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: req=req, client_error=client_error)
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: File "/opt/catweazle/lib64/python3.6/site-packages/aiohttp/connector.py", line 943, in _wrap_create_connection
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: raise client_error(req.connection_key, exc) from exc
#Apr 29 09:50:57 catweazle-3.prod.us-east-1.aws.linux.factset.com catweazle[19156]: aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host fmsmart-dns-aws-1.prod.us-east-1.aws....9', 8443)]
#Hint: Some lines were ellipsized, use -l to show in full.