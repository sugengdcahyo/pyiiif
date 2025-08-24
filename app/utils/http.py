import time
from functools import wraps
from flask import Response


def cache_headers(resp: Response, seconds=31536000, immutable=True):
    resp.headers["Cache-Control"] = f"public, max-age={seconds}" + \
        (", immutable" if immutable else "")
    return resp


def timed(logger):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            t0 = time.perf_counter()
            resp = fn(*a, **kw)
            logger.debug(
                "%s took %.1f ms", fn.__name__,
                (time.perf_counter()-t0)*1000)
            return resp
        return wrapper
    return deco
