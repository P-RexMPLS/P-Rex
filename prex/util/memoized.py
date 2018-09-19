import functools

memoized = functools.lru_cache(maxsize=None)
