from django.conf import settings

MAX_DEPTH = getattr(settings, "CACHE_HELPER_MAX_DEPTH", 10)
