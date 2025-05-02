import logging
from inspect import Signature, signature
from typing import Tuple  # deprecated, but required for Python 3.8 and below

try:
    from _pylibmc import Error as CacheSetError
except ImportError:
    from cache_helper.exceptions import CacheHelperException as CacheSetError

import functools

from django.core.cache import cache
from django.utils.functional import wraps

from cache_helper import utils

logger = logging.getLogger(__name__)


def _get_function_cache_keys(func_name: str, func_signature: Signature, args: tuple, kwargs: dict) -> Tuple[str, str]:
    """
    Generate hashed and non-hashed function cache keys, ensuring that args and kwargs are correctly bound to function.

    :param func_name: The fully specified name of the function to be cached.
    :param func_signature: The signature of the function to be cached.
    :param args: The positional arguments passed to the function.
    :param kwargs: The keyword arguments passed to the function.

    :return: A tuple containing the hashed cache key and the non-hashed cache key.
    """
    bound_arguments = func_signature.bind(*args, **kwargs)
    bound_arguments.apply_defaults()
    cache_key_string = utils.get_function_cache_key(func_name, bound_arguments.args, bound_arguments.kwargs)
    cache_key_hashed = utils.get_hashed_cache_key(cache_key_string)
    return cache_key_hashed, cache_key_string


def cached(timeout):
    def _cached(func):
        func_name = utils.get_function_name(func)
        func_signature = signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key_hashed, cache_key_string = _get_function_cache_keys(func_name, func_signature, args, kwargs)

            # We need to determine whether the object exists in the cache, and since we may have stored a literal value
            # None, use a sentinel object as the default
            sentinel = object()
            try:
                value = cache.get(cache_key_hashed, sentinel)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {cache_key_string}',
                    exc_info=True,
                )
                value = sentinel

            # If there is an issue with our cache client deserializing the value (due to memory or some other issue),
            # we get a None response so log anytime this happens
            if value is None:
                logger.warning(
                    'None cache value found for cache key: {}, function cache key: {}, value: {}'.format(
                        cache_key_hashed, cache_key_string, value
                    )
                )

            if value is sentinel or value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key_hashed, value, timeout)
                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {cache_key_string}',
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
            cache_key, _ = _get_function_cache_keys(func_name, func_signature, args, kwargs)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        return wrapper

    return _cached


def cached_class_method(timeout):
    def _cached(func):
        func_name = utils.get_function_name(func)
        func_signature = signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            # replace the first arg for caching purposes because it will be the class itself
            cls_adjusted_args = (None, *args[1:])
            cache_key_hashed, cache_key_string = _get_function_cache_keys(
                func_name, func_signature, cls_adjusted_args, kwargs
            )
            # We need to determine whether the object exists in the cache, and since we may have stored a literal value
            # None, use a sentinel object as the default
            sentinel = object()
            try:
                value = cache.get(cache_key_hashed, sentinel)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {cache_key_string}',
                    exc_info=True,
                )
                value = sentinel

            # If there is an issue with our cache client deserializing the value (due to memory or some other issue),
            # we get a None response so log anytime this happens
            if value is None:
                logger.warning(
                    'None cache value found for cache key: {}, function cache key: {}, value: {}'.format(
                        cache_key_hashed, cache_key_string, value
                    )
                )

            if value is sentinel or value is None:
                value = func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key_hashed, value, timeout)
                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {cache_key_string}',
                        exc_info=True,
                    )

            return value

        def invalidate(*args, **kwargs):
            """
            A method to invalidate a result from the cache.
            :param args: The args passed into the original function. This excludes `self` for instance methods, and
            `cls` for class methods.
            :param kwargs: The kwargs passed into the original function.
            :rtype: None
            """
            # note: args does not include the class itself, but because it *is* passed to wrapper() and we replaced
            # it with None for consistent cache behavior with subclasses, we need to account for it here by updating
            # args to include None
            cls_adjusted_args = (None, *args)
            cache_key, _ = _get_function_cache_keys(func_name, func_signature, cls_adjusted_args, kwargs)
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
            cache_key_hashed, cache_key_string = self.create_cache_key(*args, **kwargs)

            # We need to determine whether the object exists in the cache, and since we may have stored a literal value
            # None, use a sentinel object as the default
            sentinel = object()
            try:
                value = cache.get(cache_key_hashed, sentinel)
            except Exception:
                logger.warning(
                    f'Error retrieving value from Cache for Key: {cache_key_string}',
                    exc_info=True,
                )
                value = sentinel

            # If there is an issue with our cache client deserializing the value (due to memory or some other issue),
            # we get a None response so log anytime this happens
            if value is None:
                logger.warning(
                    'None cache value found for cache key: {}, function cache key: {}, value: {}'.format(
                        cache_key_hashed, cache_key_string, value
                    )
                )

            if value is sentinel or value is None:
                value = self.func(*args, **kwargs)
                # Try and set the key, value pair in the cache.
                # But if it fails on an error from the underlying
                # cache system, handle it.
                try:
                    cache.set(cache_key_hashed, value, timeout)
                except CacheSetError:
                    logger.warning(
                        f'Error saving value to Cache for Key: {cache_key_string}',
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
            cache_key_hashed, _ = self.create_cache_key(*args, **kwargs)
            cache.delete(cache_key_hashed)

        def create_cache_key(self, *args, **kwargs):
            # Need to include the first arg (self) in the cache key
            func_name = utils.get_function_name(self.func)
            func_signature = signature(self.func)
            cache_key_hashed, cache_key_string = _get_function_cache_keys(func_name, func_signature, args, kwargs)
            return cache_key_hashed, cache_key_string

    return wrapper
