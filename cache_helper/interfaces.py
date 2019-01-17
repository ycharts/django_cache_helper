class CacheHelperCacheable:
    def get_cache_helper_key(self):
        """
        For any two objects of the same class which are considered equal in your application,
        get_cache_helper_key should return the same key. This key should be unique to all objects
        considered equal. This key will be used as a component to the final cache key to get/set
        values from the cache. The key should be a string.
        """
        raise NotImplementedError
