import abc


class CacheHelperCacheable(abc.ABC):
    @abc.abstractmethod
    def get_cache_helper_key(self):
        pass
