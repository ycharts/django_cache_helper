try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError

from django.core.cache import cache
from django.utils.functional import wraps
from cache_helper import utils


def cached(timeout):
    def _cached(func):
        func_type = utils._func_type(func)

        def _get_cache_key(func_name, *args, **kwargs):
            """
            Private internal function used to get the cache key for a function given its name, type,
            and what args and kwargs were supplied to it.
            """
            function_cache_key = utils.get_function_cache_key(func_name, func_type, args, kwargs)
            return utils.sanitize_key(function_cache_key)

        def get_cache_key(*args, **kwargs):
            """
            Gets the cache key that would be used if the given args and kwargs were supplied to decorated
            function. For example, calling foo.get_cache_key('hello', 5) would not call foo - it would just
            return the cache key that would be used if you were to call foo with the same args/kwargs.
            """
            func_name = utils._func_info(func)
            cache_key = _get_cache_key(func_name, args, kwargs)
            return cache_key

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = get_cache_key(*args, **kwargs)

            try:
                value = cache.get(cache_key)
            except Exception:
                value = None

            if value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key, value, timeout)
                except CacheSetError:
                    pass

            return value

        def invalidate(*args, **kwargs):
            """
            Remove value from cache using same args/kwargs to the wrapped function originally supplied.
            For example, if you initially made a function call foo('hello', 5) which resulted
            in some value being stored inside the cache, you would call foo.invalidate('hello', 5)
            to remove that value.
            """
            cache_key = get_cache_key(*args, **kwargs)
            cache.delete(cache_key)

        wrapper.get_cache_key = get_cache_key
        wrapper.invalidate = invalidate
        return wrapper

    return _cached
