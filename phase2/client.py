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


async def call_with_retry(
    caller: Callable[[str], Awaitable[str]],
    prompt: str,
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 0.5,
) -> str:
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await caller(prompt)
        except (TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt + 1 < max_attempts:
                await asyncio.sleep(backoff_seconds * (attempt + 1))
        except Exception as exc:
            raise ModelCallError("模型调用失败且错误不可重试") from exc
    raise ModelCallError("模型调用重试次数已耗尽") from last_error


class OpenAIModelCaller:
    """延迟导入 SDK，保证没有 API Key 时离线测试仍可运行。"""

    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt

    async def __call__(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ModelCallError("请安装 openai 才能使用真实模型客户端") from exc

        client = AsyncOpenAI(
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.getenv("LLM_BASE_URL"),
        )
        response = await client.chat.completions.create(
            model=os.environ["LLM_MODEL"],
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=30,
        )
        return response.choices[0].message.content or ""
