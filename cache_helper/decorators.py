import logging

try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError

import functools

from django.core.cache import cache
from django.utils.functional import wraps

from cache_helper import utils

logger = logging.getLogger(__name__)

def cached(timeout):
    def _cached(func):
        func_name = utils.get_function_name(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            function_cache_key = utils.get_function_cache_key(func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)

            try:
                value = cache.get(cache_key)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {function_cache_key}',
                    exc_info=True,
                )
                value = None

            if value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key, value, timeout)

                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {function_cache_key}',
                        exc_info=True,
                    )

            return value

        def invalidate(*args, **kwargs):
            """
            A method to invalidate a result from the cache.
            :param args: The args passed into the original function. This includes `self` for instance methods, and
            `cls` for class methods.
            :param kwargs: The kwargs passed into the original function.
            :rtype: None
            """
            function_cache_key = utils.get_function_cache_key(func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return _cached


def cached_class_method(timeout):
    def _cached(func):
        func_name = utils.get_function_name(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # skip the first arg because it will be the class itself
            function_cache_key = utils.get_function_cache_key(
                func_name, args[1:], kwargs
            )
            cache_key = utils.get_hashed_cache_key(function_cache_key)

            try:
                value = cache.get(cache_key)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {function_cache_key}',
                    exc_info=True,
                )
                value = None

            if value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key, value, timeout)
                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {function_cache_key}',
                        exc_info=True,
                    )

            return value

        def invalidate(*args, **kwargs):
            """
            A method to invalidate a result from the cache.
            :param args: The args passed into the original function. This includes `self` for instance methods, and
            `cls` for class methods.
            :param kwargs: The kwargs passed into the original function.
            :rtype: None
            """
            function_cache_key = utils.get_function_cache_key(func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return _cached


def cached_instance_method(timeout):
    """
    Fact 1: We need to store the instance as part of the cache key
    Fact 2: To find the correct cache key to invalidate, we need to know the instance
    Fact 3: If we don't store the instance as part of the wrapper class, users of this decorator would have to
            pass `self` as the first argument to every call of invalidate

    Conclusion: We want the wrapper class to be able to automatically include the instance as the first argument to
                both `__call__` and `invalidate`

    To take care of the above requirements, we override __get__ to use functools.partial to automatically include
    obj as the first argument. See the comments in __get__ for more details.
    """

    class wrapper:
        def __init__(self, func):
            self.func = func

        def __get__(self, obj, objtype):
            # When a user calls the instance method, this partial object is what actually gets called.
            # It behaves exactly like `__call__` with `obj` automatically included as the first argument.
            fn = functools.partial(self.__call__, obj)
            # When a user calls invalidate, this partial object is what actually gets called.
            # It behaves exactly like `_invalidate` with `obj` automatically included as the first argument.
            fn.invalidate = functools.partial(self._invalidate, obj)

            return fn

        def __call__(self, *args, **kwargs):
            cache_key, function_cache_key = self.create_cache_key(*args, **kwargs)
            try:
                value = cache.get(cache_key)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {function_cache_key}',
                    exc_info=True,
                )
                value = None
            if value is None:
                value = self.func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key, value, timeout)
                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {function_cache_key}',
                        exc_info=True,
                    )
            return value

        def _invalidate(self, *args, **kwargs):
            """
            A method to invalidate a result from the cache.
            :param args: The args passed into the original function. This includes `self` for instance methods, and
            `cls` for class methods.
            :param kwargs: The kwargs passed into the original function.
            :rtype: None
            """
            cache_key, _ = self.create_cache_key(*args, **kwargs)
            cache.delete(cache_key)

        def create_cache_key(self, *args, **kwargs):
            # Need to include the first arg (self) in the cache key
            func_name = utils.get_function_name(self.func)
            function_cache_key = utils.get_function_cache_key(func_name, args, kwargs)
            cache_key = utils.get_hashed_cache_key(function_cache_key)
            return cache_key, function_cache_key

    return wrapper
