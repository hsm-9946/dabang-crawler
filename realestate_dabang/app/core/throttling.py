from __future__ import annotations

import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from loguru import logger

from .. import config

F = TypeVar("F", bound=Callable[..., Any])


def random_sleep(min_seconds: float | None = None, max_seconds: float | None = None) -> None:
    """랜덤 슬립으로 요청 속도 제어."""
    lo = min_seconds if min_seconds is not None else config.RANDOM_DELAY_MIN
    hi = max_seconds if max_seconds is not None else config.RANDOM_DELAY_MAX
    duration = random.uniform(lo, hi)
    time.sleep(duration)


def with_retry(max_tries: int | None = None) -> Callable[[F], F]:
    """재시도 데코레이터. 예외 발생 시 최대 N회 재시도."""

    tries = max_tries if max_tries is not None else config.RETRY_MAX_TRIES

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    attempt += 1
                    if attempt >= tries:
                        logger.error("재시도 초과: {} ({}회)", e, attempt)
                        raise
                    delay = random.uniform(
                        config.RANDOM_DELAY_MIN * attempt,
                        config.RANDOM_DELAY_MAX * attempt,
                    )
                    logger.warning("오류 발생, 재시도 {}회/{}회 후 {:.2f}s 대기: {}", attempt, tries, delay, e)
                    time.sleep(delay)

        return wrapper  # type: ignore[return-value]

    return decorator


