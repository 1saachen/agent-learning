import asyncio
from copy import deepcopy

from stages.phase3_personal_agent.app.agent import AgentRunner
from stages.phase3_personal_agent.app.client import ModelCallError
from stages.phase3_personal_agent.app.contracts import (
    AssistantDecision,
    CreateTodoArgs,
    GetWeatherArgs,
    ToolCall,
)
from stages.phase3_personal_agent.app.registry import ToolRegistry, ToolSpec


class SequenceModel:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.message_snapshots = []

    async def complete(self, messages, tools):
        self.message_snapshots.append(deepcopy(messages))
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


def _registry(executions):
    async def weather(args: GetWeatherArgs):
        executions.append(("get_weather", args.city))
        return {"temperature_c": 18.2, "location": args.city}

    async def todo(args: CreateTodoArgs):
        executions.append(("create_todo", args.title))
        return {"id": "todo-1", "title": args.title, "priority": args.priority}

    return ToolRegistry(
        [
            ToolSpec("get_weather", "查询天气", GetWeatherArgs, weather),
            ToolSpec("create_todo", "创建待办", CreateTodoArgs, todo),
        ]
    )


def test_agent_executes_tool_then_returns_final_answer():
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="get_weather",
                        arguments='{"city":"上海"}',
                    )
                ]
            ),
            AssistantDecision(content="上海当前 18.2 摄氏度。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry([]), max_steps=5).run("上海天气如何？"))

    assert result.stop_reason == "completed"
    assert result.steps == 2
    assert result.trace[0].tool_name == "get_weather"
    tool_message = model.message_snapshots[1][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call-1"


def test_agent_queries_weather_then_creates_todo():
    executions = []
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[ToolCall(id="weather", name="get_weather", arguments='{"city":"上海"}')]
            ),
            AssistantDecision(
                tool_calls=[
                    ToolCall(
                        id="todo",
                        name="create_todo",
                        arguments='{"title":"出门带外套","priority":"high"}',
                    )
                ]
            ),
            AssistantDecision(content="上海低于 20 度，已创建高优先级待办。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry(executions)).run("低于 20 度就创建待办"))

    assert executions == [("get_weather", "上海"), ("create_todo", "出门带外套")]
    assert [entry.step for entry in result.trace] == [1, 2]
    assert result.stop_reason == "completed"


def test_agent_handles_multiple_tool_calls_in_one_step():
    executions = []
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[
                    ToolCall(id="w", name="get_weather", arguments='{"city":"上海"}'),
                    ToolCall(id="t", name="create_todo", arguments='{"title":"复习 Agent"}'),
                ]
            ),
            AssistantDecision(content="两个工具均已执行。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry(executions)).run("查询并记录"))

    assert len(result.trace) == 2
    assert {entry.step for entry in result.trace} == {1}
    assert len([m for m in model.message_snapshots[1] if m["role"] == "tool"]) == 2


def test_agent_blocks_duplicate_tool_call_before_side_effect():
    executions = []
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[ToolCall(id="call-1", name="create_todo", arguments='{"title":"带外套"}')]
            ),
            AssistantDecision(
                tool_calls=[ToolCall(id="call-2", name="create_todo", arguments='{ "title": "带外套" }')]
            ),
            AssistantDecision(content="待办已创建一次。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry(executions)).run("创建待办"))

    assert executions == [("create_todo", "带外套")]
    assert [entry.ok for entry in result.trace] == [True, False]
    assert result.trace[1].summary == "duplicate_tool_call"


def test_agent_stops_at_max_steps():
    model = SequenceModel(
        [
            AssistantDecision(tool_calls=[ToolCall(id="1", name="get_weather", arguments='{"city":"上海"}')]),
            AssistantDecision(tool_calls=[ToolCall(id="2", name="get_weather", arguments='{"city":"北京"}')]),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry([]), max_steps=2).run("查询天气"))

    assert result.stop_reason == "max_steps_exceeded"
    assert result.steps == 2
    assert "最大步骤" in result.answer


def test_agent_preserves_trace_when_model_fails():
    model = SequenceModel(
        [
            AssistantDecision(tool_calls=[ToolCall(id="1", name="get_weather", arguments='{"city":"上海"}')]),
            ModelCallError("provider down"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry([])).run("查询天气"))

    assert result.stop_reason == "model_error"
    assert len(result.trace) == 1
    assert "模型调用失败" in result.answer
