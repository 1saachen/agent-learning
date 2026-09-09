import asyncio
import pytest

from phase2.client import FakeModelCaller, ModelCallError, OpenAIModelCaller, call_with_retry


def test_fake_caller_returns_configured_json():
    caller = FakeModelCaller('{"ok":true}')
    assert asyncio.run(caller("prompt")) == '{"ok":true}'


def test_retry_retries_timeout_then_succeeds():
    attempts = 0

    async def flaky(_: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise TimeoutError("temporary")
        return "ok"

    assert asyncio.run(call_with_retry(flaky, "p", max_attempts=2, backoff_seconds=0)) == "ok"
    assert attempts == 2


def test_retry_stops_after_max_attempts():
    async def failing(_: str) -> str:
        raise TimeoutError("down")

    with pytest.raises(ModelCallError):
        asyncio.run(call_with_retry(failing, "p", max_attempts=2, backoff_seconds=0))


def test_retry_handles_openai_style_timeout_error():
    class APITimeoutError(Exception):
        pass

    attempts = 0

    async def flaky(_: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise APITimeoutError("temporary")
        return "ok"

    assert asyncio.run(call_with_retry(flaky, "p", max_attempts=2, backoff_seconds=0)) == "ok"


def test_deepseek_defaults_match_openai_compatible_api():
    caller = OpenAIModelCaller("system")
    assert caller.base_url == "https://api.deepseek.com"
    assert caller.model == "deepseek-v4-pro"
    assert caller.api_key_env == "DEEPSEEK_API_KEY"
    assert caller.use_response_format is False
