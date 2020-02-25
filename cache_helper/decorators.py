try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError

from django.core.cache import cache
from django.utils.functional import wraps

from cache_helper import utils
from cache_helper.exceptions import CacheHelperFunctionError


def cached(timeout):

    def _cached(func):
        func_type = utils.get_function_type(func)
        if func_type is None:
            raise CacheHelperFunctionError('Error determining function type of {func}'.format(func=func))

        func_name = utils.get_function_name(func)
        if func_name is None:
            raise CacheHelperFunctionError('Error determining function name of {func}'.format(func=func))

        @wraps(func)
        def wrapper(*args, **kwargs):
            function_cache_key = utils.get_function_cache_key(func_type, func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)

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
            function_cache_key = utils.get_function_cache_key(func_type, func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return _cached
