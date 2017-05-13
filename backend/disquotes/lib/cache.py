from disquotes.model.handlers import redis_pool
from dogpile.cache import make_region

redis_cache = make_region().configure(
    'dogpile.cache.redis',
    expiration_time=3600,
    arguments={
        "connection_pool": redis_pool
    },
)
