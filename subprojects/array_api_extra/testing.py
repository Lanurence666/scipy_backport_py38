try:
    from array_api_extra.testing import lazy_xp_function
except ImportError:
    def lazy_xp_function(func, **kwargs):
        return func
