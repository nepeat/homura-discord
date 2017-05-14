import asyncio_redis
from asyncio_redis.encoders import UTF8Encoder


class BotEncoder(UTF8Encoder):
    """Modified encoder that converts integers to strings"""
    def encode_from_native(self, data):
        if isinstance(data, int):
            data = ":py_int:" + str(data)

        return super().encode_from_native(data)

    def decode_to_native(self, data):
        decoded = super().decode_to_native(data)

        if decoded.startswith(":py_int:"):
            return int(decoded.lstrip(":py_int:"))

        return decoded


class UncheckedRedisProtocol(asyncio_redis.RedisProtocol):
    def __init__(self, *args, **kwargs):
        return super().__init__(enable_typechecking=False, *args, **kwargs)
