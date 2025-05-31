import sys

import redis
from flask import current_app
from flask_sse import sse


def redis_available(url):
    try:
        r = redis.Redis.from_url(url)
        r.ping()
        return True
    except Exception:
        return False


class RedisJobStream:
    """Streams log messages to a Redis-backed SSE channel for a specific job."""

    def __init__(self, job_id):
        self.job_id = job_id

    def write(self, *args):
        s = ""
        for arg in args:
            s += " " + str(arg)
        with current_app.app_context():
            try:
                sse.publish({"data": s}, channel=self.job_id)
            except AttributeError:
                try:
                    sys.stdout.write(" * Orphaned Message: " + s)
                except Exception:
                    pass

    def flush(self):
        # This method is required for stream-like objects but is intentionally left empty.
        pass
