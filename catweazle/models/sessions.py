import uuid

import aioredis

from catweazle.models.mixins import Format
from catweazle.errors import SessionError


class Sessions(Format):
    def __init__(self, redis_host, redis_port, redis_pass):
        super().__init__()
        self._redis_host = redis_host
        self._redis_port = redis_port
        self._redis_pass = redis_pass
        self._redis = None

    @property
    def redis_host(self):
        return self._redis_host

    @property
    def redis_port(self):
        return self._redis_port

    @property
    def redis_pass(self):
        return self._redis_pass

    @property
    def redis(self):
        return self._redis

    async def init_redis(self):
        self._redis = await aioredis.create_redis_pool(
            (self.redis_host, int(self.redis_port)), password=self.redis_pass, encoding='utf-8')

    async def create(self, user):
        sid = str(uuid.uuid4())
        if not self.redis:
            await self.init_redis()
        await self.redis.set(sid, user)
        await self.redis.expire(sid, 3600)
        return self._format({'id': sid})

    async def delete(self, request):
        sid = request.cookies.get('DEPLOYER_SESSION')
        if not sid:
            return
        try:
            sid = request.cookies.get('DEPLOYER_SESSION')
        except KeyError:
            raise SessionError
        if not self.redis:
            await self.init_redis()
        await self.redis.delete(sid)

    async def get_user(self, request):
        sid = request.cookies.get('DEPLOYER_SESSION')
        if not sid:
            raise SessionError
        if not self.redis:
            await self.init_redis()
        user = await self.redis.get(sid)
        if user is not None:
            await self.redis.expire(sid, 3600)
        return self._format({'id': sid, 'user': user})

