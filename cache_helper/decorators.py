from django.core.cache import cache
from django.utils.functional import wraps
from cache_helper import utils


def cached(timeout):
    def get_key(*args, **kwargs):
        return utils.sanitize_key(utils._cache_key(*args, **kwargs))

    def _cached(func, *args):
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
                cache.set(key, value, timeout)

            return value

        def invalidate(*args, **kwargs):
            name = utils._func_info(func, args)
            key = get_key(name, func_type, args, kwargs)
            cache.delete(key)
        wrapper.invalidate = invalidate
        return wrapper
    return _cached
