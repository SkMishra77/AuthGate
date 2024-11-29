import asyncio
import time
from uuid import uuid4

import redis.exceptions
from redis.asyncio import Redis

from model.model import User
from settings import TOKEN_ACTIVE_TIME


class AuthGate:
    def __init__(self, host='localhost', port=6379, url=None, retry_attempts=3, retry_delay=2):
        self.host = host
        self.port = port
        self.url = url
        self.r: Redis | None = None
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

    @classmethod
    async def create(cls, retry_attempts=2, retry_delay=3, host='localhost', port=6379, url=None):
        try:
            instance = cls(host, port, url, retry_attempts, retry_delay)
            await instance.connect()
            return instance
        except Exception as e:
            print(f'Failed to connect to Redis: {e}')
            return None

    async def connect(self):
        try:
            if self.url is None:
                self.r = Redis(host=self.host, port=self.port, decode_responses=True)
            else:
                self.r = Redis.from_url(url=self.url, decode_responses=True)
            await self.r.ping()
            print("Connected to Redis successfully")
        except Exception as e:
            print(f"Initial connection failed: {e}")
            raise

    async def reconnect(self):
        for attempt in range(self.retry_attempts):
            try:
                await self.connect()
                return True
            except Exception as e:
                print(f"Reconnection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self.retry_delay)
        print("Failed to reconnect after multiple attempts")
        return False

    async def is_connected(self):
        try:
            await self.r.ping()
            return True
        except redis.exceptions.ConnectionError as e:
            if await self.reconnect():
                return True
            return False

    async def create_token(self, user_obj: User):
        session_token = str(uuid4())
        pipe = self.r.pipeline()
        SESSION_ACTIVE_TIME_SECONDS = TOKEN_ACTIVE_TIME.total_seconds()
        await pipe.set(f'{session_token}::token', user_obj.id)
        await pipe.expire(f'{session_token}::token', int(SESSION_ACTIVE_TIME_SECONDS))
        USER_TOKEN_EXP_TIME = int(time.mktime(time.gmtime())) + SESSION_ACTIVE_TIME_SECONDS
        await pipe.zadd(f'User::{user_obj.id}::token', {session_token: USER_TOKEN_EXP_TIME})
        await pipe.execute()
        return session_token, USER_TOKEN_EXP_TIME

    async def validate_token(self, session_token):
        user_id = await self.r.get(f'{session_token}::token')
        if user_id is None:
            return None
        CURRENT_TIME = int(time.mktime(time.gmtime()))
        await self.r.zremrangebyscore(f'User::{user_id}::token', '-inf', CURRENT_TIME - 1)
        return user_id

    async def refresh_token(self, session_token):
        user_id = await self.r.get(f'{session_token}::token')

        if user_id is None:
            return None

        CURRENT_TIME = int(time.mktime(time.gmtime()))
        SESSION_ACTIVE_TIME_SECONDS = TOKEN_ACTIVE_TIME.total_seconds()

        await self.r.expire(f'{session_token}::token', int(SESSION_ACTIVE_TIME_SECONDS))
        USER_TOKEN_EXP_TIME = CURRENT_TIME + SESSION_ACTIVE_TIME_SECONDS
        await self.r.zadd(f'User::{user_id}::token', {session_token: USER_TOKEN_EXP_TIME})
        return USER_TOKEN_EXP_TIME

    async def logout(self, session_token):
        user_id = await self.r.get(f'{session_token}::token')

        if user_id is None:
            return None  # Token doesn't exist

        await self.r.delete(f'{session_token}::token')
        await self.r.zrem(f'User::{user_id}::token', session_token)

        return True

    async def logout_all(self, session_token):
        user_id = await self.validate_token(session_token)
        if user_id is None:
            return None

        session_tokens = await self.r.zrange(f'User::{user_id}::token', 0, -1)
        pipe = self.r.pipeline()
        await pipe.zrem(f'User::{user_id}::token', *session_tokens)
        for token in session_tokens:
            await pipe.delete(f'{token}::token')
        await pipe.execute()

        return True
