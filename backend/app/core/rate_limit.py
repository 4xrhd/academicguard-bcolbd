import logging
import redis.asyncio as redis
from fastapi import HTTPException
from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

_redis_client: redis.Redis | None = None
_cached_redis_url: str | None = None


def get_redis() -> redis.Redis:
    global _redis_client, _cached_redis_url
    settings = get_settings()
    if _redis_client is None or _cached_redis_url != settings.REDIS_URL:
        _cached_redis_url = settings.REDIS_URL
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


import time

_fallback_store: dict[str, dict[str, float]] = {}

def _get_fallback_attempts(key: str) -> int:
    now = time.time()
    record = _fallback_store.get(key)
    if record:
        if now > record.get('expires_at', 0):
            _fallback_store.pop(key, None)
            return 0
        return int(record.get('attempts', 0))
    return 0

def _increment_fallback_attempts(key: str) -> None:
    now = time.time()
    record = _fallback_store.get(key)
    if not record or now > record.get('expires_at', 0):
        _fallback_store[key] = {'attempts': 1, 'expires_at': now + (LOCKOUT_MINUTES * 60)}
    else:
        record['attempts'] += 1

def _clear_fallback_attempts(key: str) -> None:
    _fallback_store.pop(key, None)


async def check_login_rate_limit(email: str, ip: str = ""):
    """
    Checks if the given email/IP has exceeded the maximum allowed failed login attempts.
    Raises HTTPException (429) if locked out.
    """
    key = f"login_attempts:{email}:{ip}" if ip else f"login_attempts:{email}"
    try:
        client = get_redis()
        attempts = await client.get(key)
        if attempts and int(attempts) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed login attempts. Account locked for {LOCKOUT_MINUTES} minutes."
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Redis unavailable during login rate limit check, using memory fallback: %s", exc)
        attempts = _get_fallback_attempts(key)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=f"Too many failed login attempts. Account locked for {LOCKOUT_MINUTES} minutes."
            )


async def record_failed_login(email: str, ip: str = ""):
    """
    Records a failed login attempt for the given email/IP.
    Sets an expiration on the key if this is the first failure.
    """
    key = f"login_attempts:{email}:{ip}" if ip else f"login_attempts:{email}"
    try:
        client = get_redis()
        attempts = await client.incr(key)
        if attempts == 1:
            # Only set expiration on the first failed attempt to define the lockout window
            await client.expire(key, LOCKOUT_MINUTES * 60)
    except Exception as exc:
        logger.warning("Redis unavailable during record_failed_login, using memory fallback: %s", exc)
        _increment_fallback_attempts(key)


async def clear_login_attempts(email: str, ip: str = ""):
    """
    Clears any recorded failed login attempts upon successful authentication.
    """
    key = f"login_attempts:{email}:{ip}" if ip else f"login_attempts:{email}"
    try:
        client = get_redis()
        await client.delete(key)
    except Exception as exc:
        logger.warning("Redis unavailable during clear_login_attempts: %s", exc)
    finally:
        _clear_fallback_attempts(key)
