try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError


from django.core.cache import cache
from django.utils.functional import wraps

from cache_helper import utils

def cached(timeout):

    def _cached(func):
        func_name = utils.get_function_name(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            function_cache_key = utils. get_function_cache_key(func_name, args, kwargs)
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

        return wrapper
    return _cached


def cached_class_method(timeout):

    def _cached(func):
        func_name = utils.get_function_name(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # skip the first arg because it will be the class itself
            function_cache_key = utils. get_function_cache_key(func_name, args[1:], kwargs)
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

        return wrapper
    return _cached


def cached_instance_method(timeout):

    def _cached(func):
        func_name = utils.get_function_name(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Need to include the first arg (self) in the cache key
            function_cache_key = utils.get_function_cache_key(func_name, args, kwargs)
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

        return wrapper
    return _cached
