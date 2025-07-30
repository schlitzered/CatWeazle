import asyncio
import logging

import bonsai.asyncio
import bonsai.errors
import bonsai.pool

from catweazle.errors import AuthenticationError
from catweazle.errors import LdapInvalidDN
from catweazle.errors import LdapResourceNotFound
from catweazle.errors import LdapNoBackend


class CrudLdap:
    def __init__(
        self,
        log: logging.Logger,
        ldap_base_dn: str,
        ldap_bind_dn: str,
        ldap_pool: bonsai.asyncio.AIOConnectionPool,
        ldap_url: str,
        ldap_user_pattern: str,
    ):
        self._log = log
        self._ldap_base_dn = ldap_base_dn
        self._ldap_bind_dn = ldap_bind_dn
        self._ldap_pool = ldap_pool
        self._ldap_url = ldap_url
        self._ldap_user_pattern = ldap_user_pattern

    @property
    def log(self):
        return self._log

    @property
    def ldap_base_dn(self):
        return self._ldap_base_dn

    @property
    def ldap_bind_dn(self):
        return self._ldap_bind_dn

    @property
    def ldap_pool(self):
        if not self._ldap_pool:
            raise LdapNoBackend
        return self._ldap_pool

    @property
    def ldap_url(self):
        return self._ldap_url

    @property
    def ldap_user_pattern(self):
        return self._ldap_user_pattern

    async def _ldap_search(
        self,
        base_dn: str,
        scope: bonsai.LDAPSearchScope,
        query: str,
    ):
        counter = self.ldap_pool.max_connection + 3
        while counter >= 0:
            conn = await self.ldap_pool.get()
            try:
                return await conn.search(base_dn, scope, query)
            except bonsai.pool.EmptyPool:
                self.log.warning("ldap pool empty, waiting 1 second")
                await asyncio.sleep(1)
            except bonsai.errors.ConnectionError:
                conn.close()
                if counter == 0:
                    self.log.error("lost ldap connection, no more retries left")
                else:
                    self.log.error(f"lost ldap connection, {counter} retries left")
                    counter -= 1
            finally:
                await self.ldap_pool.put(conn)

    async def check_user_credentials(self, user: str, password: str):
        if not self.ldap_url:
            raise AuthenticationError
        client = bonsai.LDAPClient(self.ldap_url)
        user_name = self.ldap_user_pattern.format(user)
        client.set_credentials("SIMPLE", user_name, password)
        try:
            async with client.connect(is_async=True) as conn:
                user = await conn.search(
                    self.ldap_base_dn,
                    bonsai.LDAPSearchScope.SUBTREE,
                    f"(userPrincipalName={user_name})",
                )
        except bonsai.errors.AuthenticationError:
            raise AuthenticationError
        return user[0]

    async def get_login(self, user: str):
        user_cn, user_base = user.split(",", maxsplit=1)
        user = await self._ldap_search(
            base_dn=user_base, scope=bonsai.LDAPSearchScope.ONELEVEL, query=user_cn
        )
        return user[0]["sAMAccountName"]

    async def get_logins_from_group(self, group: str):
        try:
            group_cn, group_base = group.split(",", maxsplit=1)
        except ValueError:
            raise LdapInvalidDN
        ldap_group = await self._ldap_search(
            base_dn=group_base, scope=bonsai.LDAPSearchScope.ONELEVEL, query=group_cn
        )
        try:
            ldap_group = ldap_group[0]
        except IndexError:
            raise LdapResourceNotFound
        jobs = []
        for user in ldap_group["member"]:
            jobs.append(asyncio.create_task(self.get_login(user=user)))
        if not jobs:
            self.log.warning(f"ldap group has no members: {group}")
            return []
        done, _ = await asyncio.wait(jobs, return_when=asyncio.ALL_COMPLETED)
        logins = []
        for job in done:
            logins.append(job.result()[0])
        return logins
