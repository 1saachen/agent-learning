import json
from time import perf_counter
from typing import Any

from .client import ChatModel, ModelCallError
from .contracts import (
    AgentRunResult,
    AssistantDecision,
    ToolCall,
    ToolExecutionResult,
    TraceEntry,
)
from .prompts import SYSTEM_PROMPT
from .registry import ToolRegistry


class AgentRunner:
    def __init__(
        self,
        model: ChatModel,
        registry: ToolRegistry,
        *,
        max_steps: int = 5,
    ):
        if max_steps < 1:
            raise ValueError("max_steps 必须大于 0")
        self.model = model
        self.registry = registry
        self.max_steps = max_steps

    async def run(self, user_input: str) -> AgentRunResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ]
        trace: list[TraceEntry] = []
        seen_calls: set[tuple[str, str]] = set()

        for step in range(1, self.max_steps + 1):
            try:
                decision = await self.model.complete(messages, self.registry.definitions())
            except ModelCallError:
                return AgentRunResult(
                    answer="模型调用失败，请稍后重试。",
                    stop_reason="model_error",
                    steps=step - 1,
                    trace=trace,
                )

            messages.append(_assistant_message(decision))
            if not decision.tool_calls:
                return AgentRunResult(
                    answer=decision.content or "模型没有返回可用回答。",
                    stop_reason="completed",
                    steps=step,
                    trace=trace,
                )

            for call in decision.tool_calls:
                signature, parsed_arguments = _call_signature(call)
                started = perf_counter()
                if signature in seen_calls:
                    result = ToolExecutionResult(
                        ok=False,
                        tool_name=call.name,
                        error_type="duplicate_tool_call",
                        message="相同工具和参数已经调用过，本次未重复执行",
                    )
                    validated_arguments = parsed_arguments
                else:
                    seen_calls.add(signature)
                    result, validated_arguments = await self.registry.execute(
                        call.name,
                        call.arguments,
                    )
                duration_ms = (perf_counter() - started) * 1000
                summary = result.message if result.ok else (result.error_type or result.message)
                trace.append(
                    TraceEntry(
                        step=step,
                        tool_call_id=call.id,
                        tool_name=call.name,
                        arguments=validated_arguments,
                        ok=result.ok,
                        summary=summary,
                        duration_ms=duration_ms,
                    )
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": result.model_dump_json(),
                    }
                )

        return AgentRunResult(
            answer="已达到 Agent 最大步骤数，任务未能在预算内完成。",
            stop_reason="max_steps_exceeded",
            steps=self.max_steps,
            trace=trace,
        )


def _assistant_message(decision: AssistantDecision) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": decision.content,
    }
    if decision.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": call.arguments,
                },
            }
            for call in decision.tool_calls
        ]
    return message


def _call_signature(call: ToolCall) -> tuple[tuple[str, str], dict[str, Any]]:
    try:
        parsed = json.loads(call.arguments)
    except (json.JSONDecodeError, TypeError):
        return (call.name, call.arguments), {}
    if not isinstance(parsed, dict):
        return (call.name, json.dumps(parsed, ensure_ascii=False, sort_keys=True)), {}
    canonical = json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (call.name, canonical), parsed
