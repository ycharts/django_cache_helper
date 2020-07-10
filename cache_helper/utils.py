from hashlib import sha256

from cache_helper import settings
from cache_helper.exceptions import CacheKeyCreationError
from cache_helper.interfaces import CacheHelperCacheable


def get_function_cache_key(func_name, func_args, func_kwargs):
    args_string = _sanitize_args(*func_args, **func_kwargs)
    key = '{func_name}{args_string}'.format(func_name=func_name, args_string=args_string)
    return key


def get_hashed_cache_key(key):
    """
    Given the intermediate key produced by a function call along with its args + kwargs,
    performs a sha256 hash on the utf-8 encoded version of the key, and returns the result
    """
    key_hash = sha256(key.encode('utf-8', errors='ignore')).hexdigest()
    return key_hash


def _sanitize_args(*args, **kwargs):
    """
    Creates unicode key from all kwargs/args
        -Note: comma separate args in order to prevent foo(1,2), foo(12, None) corner-case collisions...
    """
    key = ";{args_key};{kwargs_key}"
    args_key = tuple(_get_object_cache_key(obj) for obj in args)
    kwargs_key = ''
    for (k, v) in sorted(kwargs.items()):
        kwargs_key += str(k) + ':' + _get_object_cache_key(v)

    return key.format(args_key=args_key, kwargs_key=kwargs_key)


def get_function_name(func):
    return '{func_module}.{qualified_name}'.format(func_module=func.__module__, qualified_name=func.__qualname__)

def _get_object_cache_key(obj):
    """
    Function used to get the individual cache key for objects. Checks if the
    object is an instance of CacheHelperCacheable, which means it will have a
    get_cache_helper_key function defined for it which will be used as the key.
    Otherwise, just uses the string representation of the object.
    """
    if isinstance(obj, CacheHelperCacheable):
        return obj.get_cache_helper_key()
    else:
        return str(obj)
