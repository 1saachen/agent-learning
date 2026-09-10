import asyncio
from types import SimpleNamespace

import pytest

from stages.phase3_personal_agent.app import client as client_module
from stages.phase3_personal_agent.app.client import (
    DeepSeekChatClient,
    ModelCallError,
    ModelConfigurationError,
)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询天气",
            "parameters": {"type": "object", "properties": {}},
        },
    }
]


def _response(*, content=None, tool_calls=None):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _tool_call():
    return SimpleNamespace(
        id="call-weather-1",
        function=SimpleNamespace(name="get_weather", arguments='{"city":"上海"}'),
    )


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    async def create(self, **request):
        self.requests.append(request)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeSDK:
    def __init__(self, outcomes):
        self.completions = FakeCompletions(outcomes)
        self.chat = SimpleNamespace(completions=self.completions)


def test_client_sends_tools_and_normalizes_tool_calls(monkeypatch):
    sdk = FakeSDK([_response(tool_calls=[_tool_call()])])
    monkeypatch.setattr(client_module, "_create_openai_client", lambda **kwargs: sdk)
    client = DeepSeekChatClient(api_key="test-key", max_attempts=1)

    decision = asyncio.run(
        client.complete([{"role": "user", "content": "查天气"}], TOOLS)
    )

    assert decision.tool_calls[0].name == "get_weather"
    assert decision.tool_calls[0].arguments == '{"city":"上海"}'
    request = sdk.completions.requests[0]
    assert request["model"] == "deepseek-v4-pro"
    assert request["tools"] == TOOLS
    assert request["tool_choice"] == "auto"
    assert request["temperature"] == 0
    assert request["timeout"] == 30


def test_client_normalizes_final_content(monkeypatch):
    sdk = FakeSDK([_response(content="上海当前 18 度。")])
    monkeypatch.setattr(client_module, "_create_openai_client", lambda **kwargs: sdk)

    decision = asyncio.run(
        DeepSeekChatClient(api_key="test-key").complete(
            [{"role": "user", "content": "天气"}], TOOLS
        )
    )

    assert decision.content == "上海当前 18 度。"
    assert decision.tool_calls == []


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ModelConfigurationError, match="DEEPSEEK_API_KEY"):
        DeepSeekChatClient()


def test_client_retries_temporary_failure(monkeypatch):
    sdk = FakeSDK([TimeoutError("slow"), _response(content="完成")])
    monkeypatch.setattr(client_module, "_create_openai_client", lambda **kwargs: sdk)
    monkeypatch.setattr(client_module.asyncio, "sleep", lambda _: _completed())

    decision = asyncio.run(
        DeepSeekChatClient(api_key="test-key", max_attempts=2).complete([], TOOLS)
    )

    assert decision.content == "完成"
    assert len(sdk.completions.requests) == 2


class BadRequestError(Exception):
    status_code = 400


def test_client_does_not_retry_bad_request(monkeypatch):
    sdk = FakeSDK([BadRequestError("bad")])
    monkeypatch.setattr(client_module, "_create_openai_client", lambda **kwargs: sdk)

    with pytest.raises(ModelCallError, match="不可重试"):
        asyncio.run(
            DeepSeekChatClient(api_key="test-key", max_attempts=3).complete([], TOOLS)
        )

    assert len(sdk.completions.requests) == 1


async def _completed():
    return None
