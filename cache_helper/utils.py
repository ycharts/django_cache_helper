from hashlib import sha256

from cache_helper import settings
from cache_helper.exceptions import CacheKeyCreationError
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
    args_key = build_cache_key_using_dfs(args)
    kwargs_key = build_cache_key_using_dfs(kwargs)

    return f';{args_key};{kwargs_key}'


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

def build_cache_key_using_dfs(input_item):
    """
    Iterates down a tree of collections (e.g. a list of dicts), and uses the elements to build a deterministic cache key

    :param input_item: args or kwargs
    :return: A deterministic cache key
    """
    def _get_deterministic_iterable(iterable, _depth):
        """
        Helper function for the DFS that takes an iterable and sorts it deterministically. This is necessary so that
        equivalent dicts / sets are guaranteed to be cached using the same key

        :param iterable: The input iterable, potentially unordered
        :param _depth: The current depth of the DFS

        :return: A deterministically sorted iterable, containing tuples of elements and their depths
        :rtype: list[tuple[any, int]]
        """
        if isinstance(iterable, dict):
            sorted_dict = sorted(iterable.items())
            # Don't increase _depth since we are breaking the dict into tuples
            deterministic_iterable = [(item, _depth) for item in sorted_dict]
        elif isinstance(iterable, set):
            sorted_set = sorted(
                list(iterable),
                key=lambda x: sha256(_get_object_cache_key(x).encode('utf-8')).hexdigest()
            )
            deterministic_iterable = [(item, _depth + 1) for item in sorted_set]
        else:
            deterministic_iterable = [(item, _depth + 1) for item in iterable]

        return deterministic_iterable

    return_string = ''
    stack = [item for item in _get_deterministic_iterable(input_item, 0)]

    while stack:
        current_item, depth = stack.pop()
        if settings.MAX_DEPTH is not None and depth > settings.MAX_DEPTH:
            raise CacheKeyCreationError(f'Function args / kwargs have too many nested collections'
                                        f' for MAX_DEPTH {settings.MAX_DEPTH}')

        if hasattr(current_item, '__iter__') and not isinstance(current_item, str):
            return_string += ','
            stack.extend(_get_deterministic_iterable(current_item, depth))
        else:
            return_string += f'_get_object_cache_key(current_item)'

    return return_string
