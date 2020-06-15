import argparse
import asyncio
import configparser
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys
import time

from aiohttp import web
import aiotask_context as context
import aiohttp_remotes
import jsonschema
from motor.motor_asyncio import AsyncIOMotorClient
import pymongo

from catweazle.controller.authenticate import Authenticate as ControllerAuthenticate
from catweazle.controller.instances import Instances as ControllerInstances
from catweazle.controller.permissions import Permissions as ControllerPermissions
from catweazle.controller.users import Users as ControllerUsers
from catweazle.controller.users import UsersCredentials as ControllerUsersCredentials

from catweazle.errors import DuplicateResource

from catweazle.middleware import request_id, error_catcher

from catweazle.models.aa import AuthenticationAuthorization as ModelAuthenticationAuthorization
from catweazle.models.aws_route53 import AWSRoute53
from catweazle.models.credentials import Credentials as ModelCredentials
from catweazle.models.foreman_proxy import ForemanProxy as ModelForemanProxy
from catweazle.models.instances import Instances as ModelInstances
from catweazle.models.permissions import Permissions as ModelPermissions
from catweazle.models.sessions import Sessions as ModelSessions
from catweazle.models.users import Users as ModelUsers

from catweazle.schemes.config_main import CHECK_CONFIG_MAIN
from catweazle.schemes.config_main import CHECK_CONFIG_MONGOCOLL, CHECK_CONFIG_MONGOPOOL
from catweazle.schemes.config_main import CHECK_CONFIG_REDISPOOL


def main():
    parser = argparse.ArgumentParser(description="CatWeazle Rest API")

    parser.add_argument("--cfg", dest="cfg", action="store",
                        default="/etc/catweazle/catweazle.ini",
                        help="Full path to configuration")

    subparsers = parser.add_subparsers(help='commands', dest='method')
    subparsers.required = True

    run_parser = subparsers.add_parser('run', help='Start CatWeazle Rest API API')
    run_parser.set_defaults(method='run')

    indicies_parser = subparsers.add_parser('indices', help='create indices and exit')
    indicies_parser.set_defaults(method='indices')

    admin_parser = subparsers.add_parser('create_admin', help='create default admin user')
    admin_parser.set_defaults(method='create_admin')

    parsed_args = parser.parse_args()

    catweazle_restapi = CatWeazleRest(
        cfg=parsed_args.cfg,
    )

    if parsed_args.method == 'run':
        catweazle_restapi.run()

    elif parsed_args.method == 'indices':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(catweazle_restapi.manage_indices())
        loop.close()

    elif parsed_args.method == 'create_admin':
        loop = asyncio.get_event_loop()
        loop.run_until_complete(catweazle_restapi.create_admin())
        loop.close()


class CatWeazleRest:
    def __init__(self, cfg):
        self._config_file = cfg
        self._config = configparser.ConfigParser()
        self._config_dict = None
        self._mongo_pools = dict()
        self._mongo_colls = dict()
        self.log = logging.getLogger('application')
        self.config.read_file(open(self._config_file))
        self._config_dict = self._cfg_to_dict(self.config)
        try:
            jsonschema.validate(self.config_dict['main'], CHECK_CONFIG_MAIN)
        except jsonschema.exceptions.ValidationError as err:
            print("main section: {0}".format(err))
            sys.exit(1)

    def _acc_logging(self):
        acc_handlers = []
        access_log = self.config.get('file:logging', 'acc_log')
        access_retention = self.config.getint('file:logging', 'acc_retention')
        acc_handlers.append(TimedRotatingFileHandler(access_log, 'D', 1, access_retention))

        logger = logging.Logger('aiohttp.access')
        for handler in acc_handlers:
            logger.addHandler(handler)
        return logger

    def _app_logging(self):
        logfmt = logging.Formatter('%(asctime)sUTC - %(levelname)s - %(message)s')
        logfmt.converter = time.gmtime
        app_handlers = []
        aap_level = self.config.get('file:logging', 'app_loglevel')
        app_log = self.config.get('file:logging', 'app_log')
        app_retention = self.config.getint('file:logging', 'app_retention')
        app_handlers.append(TimedRotatingFileHandler(app_log, 'd', 1, app_retention))

        for handler in app_handlers:
            handler.setFormatter(logfmt)
            self.log.addHandler(handler)
        self.log.setLevel(aap_level)
        self.log.debug("application logger is up")

    def run(self):
        self._app_logging()
        self.log.info("starting up")
        loop = asyncio.get_event_loop()
        loop.set_task_factory(context.task_factory)
        self._setup_mongo_pools()
        self._setup_mongo_colls()
        self._validate_redis_pools()

        m_aws_route53 = self._setup_aws_pools()

        m_foreman_proxy, m_foreman_proxy_realm = self._setup_foreman_pools()

        m_instances = ModelInstances(
            self._mongo_colls['instances'],
            domain_suffix=self.config.get('main', 'domain_suffix')
        )
        m_permissions = ModelPermissions(self._mongo_colls['permissions'])
        m_sessions = ModelSessions(
            self.config.get('session:redispool', 'host', fallback='127.0.0.1'),
            self.config.get('session:redispool', 'port', fallback=6379),
            self.config.get('session:redispool', 'pass', fallback=None)
        )
        m_users = ModelUsers(self._mongo_colls['users'])
        m_users_cred = ModelCredentials(self._mongo_colls['users_credentials'])
        m_aa = ModelAuthenticationAuthorization(
            users=m_users,
            users_credentials=m_users_cred,
            permissions=m_permissions,
            sessions=m_sessions
        )

        c_authenticate = ControllerAuthenticate(sessions=m_sessions, users=m_users)
        c_instances = ControllerInstances(
            aa=m_aa, instances=m_instances,
            foreman=m_foreman_proxy, foreman_realm=m_foreman_proxy_realm,
            aws_route53=m_aws_route53,
            indicator_regex=self.config.get('main', 'indicator_regex')
        )
        c_permissions = ControllerPermissions(
            aa=m_aa, permissions=m_permissions
        )
        c_user = ControllerUsers(
            aa=m_aa, credentials=m_users_cred,
            permissions=m_permissions, users=m_users
        )
        c_user_cred = ControllerUsersCredentials(
            aa=m_aa, credentials=m_users_cred, users=m_users
        )

        app = web.Application(middlewares=[request_id, error_catcher, aiohttp_remotes.XForwardedRelaxed().middleware])

        app.router.add_static('/static/', path=str('{0}/static'.format(os.path.dirname(__file__))))

        app.router.add_route('DELETE', '/api/v1/authenticate', c_authenticate.delete)
        app.router.add_route('GET', '/api/v1/authenticate', c_authenticate.get)
        app.router.add_route('POST', '/api/v1/authenticate', c_authenticate.post)

        app.router.add_route('GET', '/api/v1/instances/_search', c_instances.search)
        app.router.add_route('DELETE', '/api/v1/instances/{instance}', c_instances.delete)
        app.router.add_route('GET', '/api/v1/instances/{instance}', c_instances.get)
        app.router.add_route('POST', '/api/v1/instances/{instance}', c_instances.post)

        app.router.add_route('GET', '/api/v1/permissions/_search', c_permissions.search)
        app.router.add_route('DELETE', '/api/v1/permissions/{perm}', c_permissions.delete)
        app.router.add_route('GET', '/api/v1/permissions/{perm}', c_permissions.get)
        app.router.add_route('POST', '/api/v1/permissions/{perm}', c_permissions.post)
        app.router.add_route('PUT', '/api/v1/permissions/{perm}', c_permissions.put)

        app.router.add_route('GET', '/api/v1/users/_search', c_user.search)
        app.router.add_route('DELETE', '/api/v1/users/{user}', c_user.delete)
        app.router.add_route('GET', '/api/v1/users/{user}', c_user.get)
        app.router.add_route('POST', '/api/v1/users/{user}', c_user.post)
        app.router.add_route('PUT', '/api/v1/users/{user}', c_user.put)

        app.router.add_route('GET', '/api/v1/users/{user}/credentials', c_user_cred.get_all)
        app.router.add_route('DELETE', '/api/v1/users/{user}/credentials/{cred}', c_user_cred.delete)
        app.router.add_route('GET', '/api/v1/users/{user}/credentials/{cred}', c_user_cred.get)
        app.router.add_route('POST', '/api/v1/users/{user}/credentials', c_user_cred.post)
        app.router.add_route('PUT', '/api/v1/users/{user}/credentials/{cred}', c_user_cred.put)

        web.run_app(
            app=app,
            host=self.config.get('main', 'host'),
            port=self.config.getint('main', 'port'),
            access_log=self._acc_logging(),
            access_log_format='%a %t "%r" %s %b "%{Referer}i" "%{User-Agent}i" %{X-Request-ID}o'
        )

        self.log.info("shutting down")

    @staticmethod
    def _cfg_to_dict(config):
        result = {}
        for section in config.sections():
            result[section] = {}
            for option in config.options(section):
                try:
                    result[section][option] = config.getint(section, option)
                    continue
                except ValueError:
                    pass
                try:
                    result[section][option] = config.getfloat(section, option)
                    continue
                except ValueError:
                    pass
                try:
                    result[section][option] = config.getboolean(section, option)
                    continue
                except ValueError:
                    pass
                try:
                    result[section][option] = config.get(section, option)
                    continue
                except ValueError:
                    pass
        return result

    def _setup_aws_pools(self):
        self.log.info("setting up aws pools")
        aws = list()
        for section in self.config.sections():
            if section.endswith(':aws'):
                sectionname = section.rsplit(':', 1)[0]
                self.log.debug("setting up aws pool {0}".format(sectionname))
                m_aws_route53 = AWSRoute53(
                    name=sectionname,
                    dry_run=self.config.getboolean('main', 'dry_run', fallback=False),
                    dns_arpa_enable=self.config.getboolean(section, 'dns_arpa_enable'),
                    dns_arpa_zones=self.config.get(section, 'dns_arpa_zones', fallback=None),
                    dns_forward_enable=self.config.getboolean(section, 'dns_forward_enable'),
                    dns_forward_zone=self.config.get(section, 'dns_forward_zone'),
                )
                aws.append(m_aws_route53)
                self.log.debug("setting up aws pool {0} done".format(sectionname))
        self.log.info("setting up aws pools done")
        return aws

    def _setup_foreman_pools(self):
        self.log.info("setting up foreman pools")
        foreman = list()
        foreman_realm = None
        for section in self.config.sections():
            if section.endswith(':foreman'):
                sectionname = section.rsplit(':', 1)[0]
                self.log.debug("setting up foreman pool {0}".format(sectionname))
                m_foreman_proxy = ModelForemanProxy(
                    name=sectionname,
                    dry_run=self.config.getboolean('main', 'dry_run', fallback=False),
                    url=self.config.get(section, 'url'),
                    ssl_crt=self.config.get(section, 'ssl_crt'),
                    ssl_key=self.config.get(section, 'ssl_key'),
                    dns_arpa_enable=self.config.getboolean(section, 'dns_arpa_enable'),
                    dns_arpa_zones=self.config.get(section, 'dns_arpa_zones', fallback=None),
                    dns_forward_enable=self.config.getboolean(section, 'dns_forward_enable'),
                    realm=self.config.get(section, 'realm', fallback=None),
                )
                foreman.append(m_foreman_proxy)
                if m_foreman_proxy.realm:
                    if foreman_realm:
                        self.log.fatal("only one foreman section is allowed to have realm_enable set to true")
                        sys.exit(1)
                    foreman_realm = m_foreman_proxy
                self.log.debug("setting up foreman pool {0} done".format(sectionname))
        self.log.info("setting up foreman pools done")
        return foreman, foreman_realm

    def _setup_mongo_pools(self):
        self.log.info("setting up mongodb connection pools")
        for section in self.config.sections():
            if section.endswith(':mongopool'):
                try:
                    jsonschema.validate(self.config_dict[section], CHECK_CONFIG_MONGOPOOL)
                except jsonschema.exceptions.ValidationError as err:
                    print("{0} section: {1}".format(section, err))
                    sys.exit(1)
                sectionname = section.rsplit(':', 1)[0]
                self.log.debug("setting up mongodb connection pool {0}".format(sectionname))
                pool = AsyncIOMotorClient(
                    host=self.config.get(section, 'hosts'),
                )
                db = pool.get_database(self.config.get(section, 'db'))
                try:
                    user = self.config.get(section, 'user')
                    password = self.config.get(section, 'pass')
                    db.authenticate(user, password)
                    self.log.debug("connection pool {0} is using authentication".format(sectionname))
                except configparser.NoOptionError:
                    self.log.debug("connection pool {0} is not using authentication".format(sectionname))
                self._mongo_pools[sectionname] = db
                self.log.debug("setting up mongodb connection pool {0} done".format(sectionname))
        self.log.info("setting up mongodb connection pools done")

    def _setup_mongo_colls(self):
        self.log.info("setting up mongodb collections")
        for section in self.config.sections():
            if section.endswith(':mongocoll'):
                try:
                    jsonschema.validate(self.config_dict[section], CHECK_CONFIG_MONGOCOLL)
                except jsonschema.exceptions.ValidationError as err:
                    print("{0} section: {1}".format(section, err))
                    sys.exit(1)
                sectionname = section.rsplit(':', 1)[0]
                self.log.debug("setting up mongodb collection {0}".format(sectionname))
                pool_name = self.config.get(section, 'pool')
                coll_name = self.config.get(section, 'coll')
                self.log.debug("mongodb collection {0} is using mongodb connection pool {1}"
                               .format(sectionname, pool_name))
                self.log.debug("mongodb collection {0} is using collection name {1}".format(sectionname, coll_name))
                pool = self._mongo_pools[pool_name]
                coll = pool.get_collection(coll_name)
                self._mongo_colls[sectionname] = coll
                self.log.debug("setting up mongodb collection {0} done".format(sectionname))
        self.log.info("setting up mongodb collections done")

    def _validate_redis_pools(self):
        self.log.info("setting up redis pools")
        for section in self.config.sections():
            if section.endswith(':redispool'):
                try:
                    jsonschema.validate(self.config_dict[section], CHECK_CONFIG_REDISPOOL)
                except jsonschema.exceptions.ValidationError as err:
                    print("{0} section: {1}".format(section, err))
                    sys.exit(1)
        self.log.info("setting up redis pools done")

    @property
    def config(self):
        return self._config

    @property
    def config_dict(self):
        return self._config_dict

    async def create_admin(self):
        self.config.read_file(open(self._config_file))
        self._config_dict = self._cfg_to_dict(self.config)
        self._setup_mongo_pools()
        self._setup_mongo_colls()

        admin = {
            "admin": True,
            "backend": "internal",
            "backend_ref": "default_admin",
            "email": "default_admin@internal",
            "name": "Default Admin User",
            "password": "password"
        }
        try:
            print("creating admin user...")
            m_users = ModelUsers(self._mongo_colls['users'])
            await m_users.create('admin', admin)
            print("done...")
        except DuplicateResource:
            print("admin user already exists...")

    async def manage_indices(self):
        self.config.read_file(open(self._config_file))
        self._config_dict = self._cfg_to_dict(self.config)
        self._setup_mongo_pools()
        self._setup_mongo_colls()

        c_instances = self._mongo_colls["instances"]
        await c_instances.create_index([
            ("id", pymongo.ASCENDING)
        ], unique=True)
        await c_instances.create_index([
            ("fqdn", pymongo.ASCENDING)
        ], unique=True)
        await c_instances.create_index([
            ("ip_address", pymongo.ASCENDING)
        ], unique=True)

        await c_instances.create_index([
            ("dns_indicator", pymongo.ASCENDING),
            ("fqdn", pymongo.ASCENDING),
            ("id", pymongo.ASCENDING),
            ("ip_address", pymongo.ASCENDING)
        ])

        c_permissions = self._mongo_colls["permissions"]
        await c_permissions.create_index([
            ("id", pymongo.ASCENDING)
        ], unique=True)
        await c_permissions.create_index([
            ("permissions", pymongo.ASCENDING)
        ])
        await c_permissions.create_index([
            ("users", pymongo.ASCENDING),
        ])

        c_users = self._mongo_colls["users"]
        await c_users.create_index([
            ("id", pymongo.ASCENDING)
        ], unique=True)

        c_users_credentials = self._mongo_colls["users_credentials"]
        await c_users_credentials.create_index([
            ("owner", pymongo.ASCENDING),
            ("id", pymongo.ASCENDING)
        ], unique=True)
