from typing import Callable

import diskcache

from src.settings import CACHE_DIR


cache = diskcache.Cache(str(CACHE_DIR))

_SENTINEL = object()  # token para distinguir 'não cacheado' de 'cacheado com valor vazio/falsy'


def cache_it(
    func: Callable,
    expire: int = 60 * 5,  # 5 min
) -> Callable:
    def wrapper(*args, **kwargs):
        key = f'{func.__name__}:{args}:{kwargs}'
        result = cache.get(key, default=_SENTINEL)
        if result is _SENTINEL:
            result = func(*args, **kwargs)
            # Só cacheia se o resultado for útil (não vazio ou None)
            if result is not None and result != [] and result != {}:
                cache.set(key, result, expire=expire)
        return result

    return wrapper
