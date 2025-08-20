import logging
from typing import List
import ssl
import sys

from catweazle.errors import BackendError

import httpx
import ipaddress
from pydantic.networks import IPv4Network


class CrudForeman:
    def __init__(
        self,
        log: logging.Logger,
        name: str,
        url: str,
        ssl_key: str,
        ssl_ca: str,
        ssl_crt: str,
        dns_arpa_enable: bool,
        dns_arpa_zones: List[IPv4Network],
        dns_forward_enable: bool,
        realm_enable: bool = False,
        realm_name: str = None,
    ):
        self._log = log
        self._dns_arpa_enable = dns_arpa_enable
        self._dns_arpa_zones = set()
        for subnet in dns_arpa_zones:
            self._dns_arpa_zones.add(ipaddress.ip_network(subnet))
        self._dns_forward_enable = dns_forward_enable
        self._name = name
        self._realm_enable = realm_enable
        self._realm_name = realm_name
        self._ssl_ca = ssl_ca
        self._ssl_crt = ssl_crt
        self._ssl_key = ssl_key
        self._url = url
        if self.ssl_key and self.ssl_crt and self.ssl_ca:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            try:
                context.load_cert_chain(certfile=self.ssl_crt, keyfile=self.ssl_key)
                context.load_verify_locations(cafile=self.ssl_ca)
            except OSError as err:
                self.log.error(
                    f"{self.name}:foreman: could not create ssl context: {err}"
                )
                sys.exit(1)
            self._http = httpx.AsyncClient(verify=context, timeout=30)
        else:
            self._http = httpx.AsyncClient(timeout=30)

    @property
    def log(self):
        return self._log

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
    def name(self):
        return self._name

    @property
    def realm_enable(self):
        return self._realm_enable

    @property
    def realm_name(self):
        return self._realm_name

    @property
    def ssl_ca(self):
        return self._ssl_ca

    @property
    def ssl_crt(self):
        return self._ssl_crt

    @property
    def ssl_key(self):
        return self._ssl_key

    @property
    def url(self):
        return self._url

    @property
    def http(self) -> httpx.AsyncClient:
        return self._http

    async def request_delete(self, url):
        url = f"{self.url}{url}"
        resp = await self.http.delete(url)
        self.log.info(f"{self.name}:foreman: request_delete: {url}")
        if resp.status_code != 200:
            self.log.error(resp.text)
            raise BackendError()

    async def request_post(self, url, data):
        url = f"{self.url}{url}"
        resp = await self.http.post(url, data=data)
        self.log.info(f"{self.name}:foreman: request_post: {url} {data}")
        if resp.status_code != 200:
            self.log.error(resp.text)
            raise BackendError()
        return resp.json()

    def arpa_responsible(self, ip_address):
        for zone in self.dns_arpa_zones:
            if ip_address in zone:
                return True
        return False

    async def create_dns(self, fqdn, ip_address):
        await self.create_arpa_dns(fqdn=fqdn, ip_address=ip_address)
        await self.create_forward_dns(fqdn=fqdn, ip_address=ip_address)

    async def create_arpa_dns(self, fqdn, ip_address):
        self.log.info(
            f"{self.name}:foreman: creating DNS PTR Record for {fqdn} with ip {ip_address}"
        )
        if not self.dns_arpa_enable:
            self.log.info(f"{self.name}:foreman: reverse DNS is disabled")
            return
        ip_addr = ipaddress.IPv4Address(ip_address)
        if self.arpa_responsible(ip_address=ip_addr):
            body_ptr = {
                "fqdn": fqdn,
                "value": ip_addr.reverse_pointer,
                "type": "PTR",
            }
            await self.request_post("/dns/", body_ptr)
        self.log.info(
            f"{self.name}:foreman: creating DNS PTR Record for {fqdn} with ip {ip_address}, done"
        )

    async def create_forward_dns(self, fqdn, ip_address):
        self.log.info(
            f"{self.name}:foreman: creating DNS A Record for {fqdn} with ip {ip_address}"
        )
        if not self.dns_forward_enable:
            self.log.info(f"{self.name}:foreman: forward DNS is disabled")
            return
        body_a = {
            "fqdn": fqdn,
            "value": ip_address,
            "type": "A",
        }
        self.log.info(
            f"{self.name}:foreman: creating DNS A Record for {fqdn} with ip {ip_address}, done"
        )

        await self.request_post("/dns/", body_a)

    async def delete_dns(self, fqdn, ip_address):
        await self.delete_arpa_dns(fqdn=fqdn, ip_address=ip_address)
        await self.delete_forward_dns(fqdn=fqdn, ip_address=ip_address)

    async def delete_arpa_dns(self, ip_address, fqdn):
        self.log.info(
            f"{self.name}:foreman: deleting DNS PTR Record for {fqdn} with ip {ip_address}"
        )
        if not self.dns_arpa_enable:
            self.log.info(f"{self.name}:foreman: reverse DNS is disabled")
            return
        ip_addr = ipaddress.IPv4Address(ip_address)
        if self.arpa_responsible(ip_address=ip_addr):
            await self.request_delete(f"/dns/{ip_addr.reverse_pointer}/PTR")
        self.log.info(
            f"{self.name}:foreman: deleting DNS PTR Record for {fqdn} with ip {ip_address}, done"
        )

    async def delete_forward_dns(self, ip_address, fqdn):
        self.log.info(
            f"{self.name}:foreman: deleting DNS A Record for {fqdn} with ip {ip_address}"
        )
        if not self.dns_forward_enable:
            self.log.info(f"{self.name}:foreman: forward DNS is disabled")
            return
        await self.request_delete(f"/dns/{fqdn}/A")
        self.log.info(
            f"{self.name}:foreman: deleting DNS A Record for {fqdn} with ip {ip_address}, done"
        )

    async def create_realm(self, fqdn):
        if not self.realm_enable:
            self.log.info(f"{self.name}:foreman: realm is disabled")
            return None
        self.log.info(f"{self.name}:foreman: creating realm entry for {fqdn}")
        body_a = {
            "hostname": fqdn,
        }
        data = await self.request_post(f"/realm/{self.realm_name}", body_a)
        self.log.info(f"{self.name}:foreman: creating realm entry for {fqdn}, done")
        return data["randompassword"]

    async def delete_realm(self, fqdn):
        if not self.realm_enable:
            self.log.info(f"{self.name}:foreman: realm is disabled")
            return
        self.log.info(f"{self.name}:foreman: deleting realm entry for {fqdn}")
        self.log.info(f"{self.name}:foreman: deleting realm entry for {fqdn}, done")
        await self.request_delete(f"/realm/{self.realm_name}/{fqdn}")
