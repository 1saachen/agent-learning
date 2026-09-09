import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Protocol


class ModelCaller(Protocol):
    async def __call__(self, prompt: str) -> str: ...


class ModelCallError(RuntimeError):
    """模型调用在有限重试后仍然失败。"""


class FakeModelCaller:
    def __init__(self, response: str):
        self.response = response

    async def __call__(self, _: str) -> str:
        return self.response


def _is_retryable_error(exc: Exception) -> bool:
    """兼容内置异常和 OpenAI SDK 异常，而不强制离线环境安装 SDK。"""
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


async def call_with_retry(
    caller: Callable[[str], Awaitable[str]],
    prompt: str,
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0.5,
) -> str:
    if max_attempts < 1:
        raise ValueError("max_attempts 必须大于 0")
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await caller(prompt)
        except Exception as exc:
            if not _is_retryable_error(exc):
                raise ModelCallError("模型调用失败且错误不可重试") from exc
            last_error = exc
            if attempt + 1 < max_attempts:
                await asyncio.sleep(backoff_seconds * (attempt + 1))
    raise ModelCallError("模型调用重试次数已耗尽") from last_error


class OpenAIModelCaller:
    """延迟导入 SDK，保证没有 API Key 时离线测试仍可运行。"""

    def __init__(
        self,
        system_prompt: str,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key_env: str = "DEEPSEEK_API_KEY",
        use_response_format: bool | None = None,
    ):
        self.system_prompt = system_prompt
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-v4-pro")
        self.api_key_env = api_key_env
        self.use_response_format = (
            use_response_format
            if use_response_format is not None
            else os.getenv("LLM_USE_RESPONSE_FORMAT", "false").lower() == "true"
        )

    async def __call__(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ModelCallError("请安装 openai 才能使用真实模型客户端") from exc

        client = AsyncOpenAI(
            api_key=os.environ[self.api_key_env],
            base_url=self.base_url,
        )
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "timeout": 30,
        }
        if self.use_response_format:
            request["response_format"] = {"type": "json_object"}
        response = await client.chat.completions.create(**request)
        return response.choices[0].message.content or ""
