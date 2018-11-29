try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError

from django.core.cache import cache
from django.utils.functional import wraps
from cache_helper import utils


def cached(timeout):
    def get_key(*args, **kwargs):
        function_cache_key = utils.get_function_cache_key(*args, **kwargs)
        return utils.sanitize_key(function_cache_key)

    def _cached(func):
        func_type = utils._func_type(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            name = utils._func_info(func, args)
            key = get_key(name, func_type, args, kwargs)

            try:
                value = cache.get(key)
            except Exception:
                value = None

            if value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(key, value, timeout)
                except CacheSetError:
                    pass

            return value

        def invalidate(*args, **kwargs):
            name = utils._func_info(func, args)
            key = get_key(name, func_type, args, kwargs)
            cache.delete(key)

        wrapper.invalidate = invalidate
        return wrapper

    return _cached
