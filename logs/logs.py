import sys
import os
import redis

redis_host = 'redis'
redis_port = 6379
r = redis.StrictRedis(host=redis_host, port=redis_port, decode_responses=True)

while True:
    try:
        work = r.blpop("logging", timeout=0)
        # No need to decode again, since `decode_responses=True` already handles that
        print(work[1])
    except Exception as exp:
        print("Exception found:", exp)
    sys.stdout.flush()
    sys.stderr.flush()
