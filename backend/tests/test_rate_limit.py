import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException

from app.core.rate_limit import check_login_rate_limit, record_failed_login, clear_login_attempts


def test_check_login_rate_limit_ok():
    mock_redis = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        mock_redis.get = AsyncMock(return_value="3")
        asyncio.run(check_login_rate_limit("test@test.com"))
        mock_redis.get.assert_called_once_with("login_attempts:test@test.com")


def test_check_login_rate_limit_locked():
    mock_redis = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        mock_redis.get = AsyncMock(return_value="5")
        with pytest.raises(HTTPException) as exc:
            asyncio.run(check_login_rate_limit("test@test.com"))
        assert exc.value.status_code == 429
        assert "Too many failed login attempts" in exc.value.detail


def test_record_failed_login_first_attempt():
    mock_redis = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        asyncio.run(record_failed_login("test@test.com"))
        mock_redis.incr.assert_called_once_with("login_attempts:test@test.com")
        mock_redis.expire.assert_called_once_with("login_attempts:test@test.com", 15 * 60)


def test_record_failed_login_subsequent_attempt():
    mock_redis = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.expire = AsyncMock()
        asyncio.run(record_failed_login("test@test.com"))
        mock_redis.incr.assert_called_once_with("login_attempts:test@test.com")
        mock_redis.expire.assert_not_called()


def test_clear_login_attempts():
    mock_redis = AsyncMock()
    with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
        mock_redis.delete = AsyncMock()
        asyncio.run(clear_login_attempts("test@test.com"))
        mock_redis.delete.assert_called_once_with("login_attempts:test@test.com")
