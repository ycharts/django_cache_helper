from hashlib import sha256

from cache_helper.interfaces import CacheHelperCacheable


def get_function_cache_key(func_name, func_args, func_kwargs):
    args_string = build_args_string(*func_args, **func_kwargs)
    key = '{func_name}{args_string}'.format(func_name=func_name, args_string=args_string)
    return key


def get_hashed_cache_key(key):
    """
    Given the intermediate key produced by a function call along with its args + kwargs,
    performs a sha256 hash on the utf-8 encoded version of the key, and returns the result
    """
    key_hash = sha256(key.encode('utf-8', errors='ignore')).hexdigest()
    return key_hash


def build_args_string(*args, **kwargs):
    """
    Deterministically builds a string from the args and kwargs. If any of the args or kwargs are an instance
    of `CacheHelperCacheable`, `get_cache_helper_key` will be called to help build the string.

    We used to iterate down the kwargs to handle the case where a CacheHelperCacheable may be deeply nested
    within the kwargs. However we are now using a simpler solution that only checks if the top-most level
    args and kwargs are `CacheHelperCacheable`. Update this function if you run into a scenario where this
    simple solution is insufficient for your needs.
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
