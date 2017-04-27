import unicodedata
from hashlib import sha256

from django.core.cache import cache

from cache_helper import settings
from cache_helper.exceptions import CacheKeyCreationError

# List of Control Characters not useable by memcached
CONTROL_CHARACTERS = set([chr(i) for i in range(0, 33)])
CONTROL_CHARACTERS.add(chr(127))

def sanitize_key(key, max_length=250):
    """
    Truncates key to keep it under memcached char limit.  Replaces with hash.
    Remove control characters b/c of memcached restriction on control chars.
    """
    key = ''.join([c for c in key if c not in CONTROL_CHARACTERS])
    key_length = len(key)
    # django memcached backend will, by default, add a prefix. Account for this in max
    # key length. '%s:%s:%s'.format()
    version_length = len(str(getattr(cache, 'version', '')))
    prefix_length = len(settings.CACHE_MIDDLEWARE_KEY_PREFIX)
    # +2 for the colons
    max_length -= (version_length + prefix_length + 2)
    if key_length > max_length:
        the_hash = sha256(key.encode('utf-8')).hexdigest()
        # sha256 always 64 chars.
        key = key[:max_length - 64] + the_hash
    return key


def _sanitize_args(args=[], kwargs={}):
    """
    Creates unicode key from all kwargs/args
        -Note: comma separate args in order to prevent poo(1,2), poo(12, None) corner-case collisions...
    """
    key = ";{0};{1}"
    kwargs_key = ""
    args_key = _plumb_collections(args)
    kwargs_key = _plumb_collections(kwargs)
    return key.format(args_key, kwargs_key)


def _func_type(func):
    argnames = func.__code__.co_varnames[:func.__code__.co_argcount]
    if len(argnames) > 0:
        if argnames[0] == 'self':
            return 'method'
        elif argnames[0] == 'cls':
            return 'class_method'
    return 'function'


def get_normalized_term(term, dash_replacement=''):
    term = str(term)
    if isinstance(term, bytes):
        term = term.decode('utf-8')
    term = unicodedata.normalize('NFKD', term).encode('ascii', 'ignore').decode('utf-8')
    term = term.lower()
    term = term.strip()
    return term


def _func_info(func, args):
    func_type = _func_type(func)
    lineno = ":%s" % func.__code__.co_firstlineno

    if func_type == 'function':
        name = ".".join([func.__module__, func.__name__]) + lineno
        return name
    elif func_type == 'class_method':
        class_name = args[0].__name__
    else:
        class_name = args[0].__class__.__name__
    name = ".".join([func.__module__, class_name, func.__name__]) + lineno
    return name


def _cache_key(func_name, func_type, args, kwargs):
    if func_type in ['method', 'function']:
        args_string = _sanitize_args(args, kwargs)
    elif func_type == 'class_method':
        args_string = _sanitize_args(args[1:], kwargs)
    key = '%s%s' % (func_name, args_string)
    return key

def _plumb_collections(input_item):
    """
    Rather than enforce a list input type, place ALL input
    in our state list.
    """
    level = 0
    return_list = []
    # really just want to make sure we start off with a list of iterators, so enforce here
    if hasattr(input_item, '__iter__'):
        if isinstance(input_item, dict):
            # Py3k Compatibility nonsense...
            remains = [[(k,v) for k, v in input_item.items()].__iter__()]
            # because dictionary iterators yield tuples, it would appear
            # to be 2 levels per dictionary, but that seems unexpected.
            level -= 1
        else:
            remains = [input_item.__iter__()]
    else:
        return get_normalized_term(input_item)

    while len(remains) > 0:
        if settings.MAX_DEPTH is not None and level > settings.MAX_DEPTH:
            raise CacheKeyCreationError('Function args or kwargs have too many nested collections for current MAX_DEPTH')
        current_iterator = remains.pop()
        level += 1
        while True:
            try:
                current_item = next(current_iterator)
            except StopIteration:
                level -= 1
                break
            # In py3k hasattr(str, '__iter__')  => True but in python 2 it's False which will break
            # this if statement. That's why we do `not isinstance(current_item, str)` check as well.
            if hasattr(current_item, '__iter__') and not isinstance(current_item, str):
                return_list.append(',')

                # Dictionaries and sets are unordered and can be of various data types
                # We use the sha256 hash on keys and sort to be deterministic
                if isinstance(current_item, dict):
                    hashed_list = []

                    for k, v in current_item.items():
                        hashed_list.append((sha256(str(k).encode('utf-8')).hexdigest(), v))

                    hashed_list = sorted(hashed_list, key=lambda t: t[0])
                    remains.append(current_iterator)
                    remains.append(hashed_list.__iter__())

                    level -= 1
                    break
                elif isinstance(current_item, set):
                    hashed_list = []

                    for object in set:
                        hashed_list.append(sha256(str(object).encode('utf-8')).hexdigest())

                    hashed_list = sorted(hashed_list)
                    remains.append(current_iterator)
                    remains.append(hashed_list.__iter__())
                    break
                else:
                    remains.append(current_iterator)
                    remains.append(current_item.__iter__())
                    break
            else:
                current_item_string = '{0},'.format(get_normalized_term(current_item))
                return_list.append(current_item_string)
                continue
    # trim trailing comma
    return_string = ''.join(return_list)
    # trim last ',' because it lacks significant meaning.
    return return_string[:-1]