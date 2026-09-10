import asyncio
import os
from typing import Any, Protocol

from .contracts import AssistantDecision, ToolCall


class ChatModel(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantDecision: ...


class ModelConfigurationError(RuntimeError):
    """模型客户端缺少必要配置。"""


class ModelCallError(RuntimeError):
    """模型调用失败。"""


def _create_openai_client(*, api_key: str, base_url: str):
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise ModelConfigurationError("请安装 openai 才能使用 DeepSeek") from exc
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    name = type(exc).__name__.lower()
    retryable_names = (
        "timeout",
        "connection",
        "ratelimit",
        "internalserver",
        "serviceunavailable",
    )
    if any(part in name for part in retryable_names):
        return True
    status_code = getattr(exc, "status_code", None)
    return isinstance(status_code, int) and (status_code == 429 or status_code >= 500)


class DeepSeekChatClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30,
        max_attempts: int = 3,
        backoff_seconds: float = 0.5,
    ):
        resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not resolved_key:
            raise ModelConfigurationError(
                "未找到 DEEPSEEK_API_KEY，请先在电脑环境变量中配置"
            )
        if max_attempts < 1:
            raise ValueError("max_attempts 必须大于 0")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-v4-pro")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self._client = _create_openai_client(api_key=resolved_key, base_url=self.base_url)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AssistantDecision:
        request = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": 0,
            "timeout": self.timeout_seconds,
        }
        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                response = await self._client.chat.completions.create(**request)
                return _normalize_response(response)
            except Exception as exc:
                if not _is_retryable_error(exc):
                    raise ModelCallError("模型调用失败且错误不可重试") from exc
                last_error = exc
                if attempt + 1 < self.max_attempts:
                    await asyncio.sleep(self.backoff_seconds * (attempt + 1))
        raise ModelCallError("模型调用重试次数已耗尽") from last_error


def _normalize_response(response: Any) -> AssistantDecision:
    try:
        message = response.choices[0].message
        tool_calls = [
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=call.function.arguments,
            )
            for call in (message.tool_calls or [])
        ]
        return AssistantDecision(content=message.content, tool_calls=tool_calls)
    except (AttributeError, IndexError, TypeError) as exc:
        raise ModelCallError("模型返回了无法识别的响应结构") from exc
