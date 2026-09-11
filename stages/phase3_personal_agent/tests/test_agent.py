import asyncio
from copy import deepcopy

from stages.phase3_personal_agent.app.agent import AgentRunner
from stages.phase3_personal_agent.app.client import ModelCallError
from stages.phase3_personal_agent.app.conversation import Conversation
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


def test_agent_detects_duplicate_after_pydantic_normalization():
    executions = []
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[ToolCall(id="call-1", name="create_todo", arguments='{"title":"带外套"}')]
            ),
            AssistantDecision(
                tool_calls=[
                    ToolCall(
                        id="call-2",
                        name="create_todo",
                        arguments='{"title":"  带外套  ","priority":"medium","due_date":null}',
                    )
                ]
            ),
            AssistantDecision(content="待办只创建了一次。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry(executions)).run("创建待办"))

    assert executions == [("create_todo", "带外套")]
    assert result.trace[1].summary == "duplicate_tool_call"


def test_successful_trace_contains_bounded_result_summary():
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[ToolCall(id="weather", name="get_weather", arguments='{"city":"上海"}')]
            ),
            AssistantDecision(content="查询完成。"),
        ]
    )

    result = asyncio.run(AgentRunner(model, _registry([])).run("查询天气"))

    assert "18.2" in result.trace[0].summary
    assert "上海" in result.trace[0].summary
    assert len(result.trace[0].summary) <= 300


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


def test_conversation_reuses_complete_answer_history_across_runs():
    model = SequenceModel(
        [
            AssistantDecision(content="第一轮回答"),
            AssistantDecision(content="第二轮回答"),
        ]
    )
    conversation = Conversation()
    runner = AgentRunner(model, _registry([]))

    first = asyncio.run(runner.run("第一轮问题", conversation=conversation))
    second = asyncio.run(runner.run("第二轮问题", conversation=conversation))

    assert first.answer == "第一轮回答"
    assert second.answer == "第二轮回答"
    assert model.message_snapshots[1] == [
        {"role": "system", "content": conversation.messages[0]["content"]},
        {"role": "user", "content": "第一轮问题"},
        {"role": "assistant", "content": "第一轮回答"},
        {"role": "user", "content": "第二轮问题"},
    ]
    assert conversation.messages[-1] == {"role": "assistant", "content": "第二轮回答"}


def test_conversation_keeps_tool_call_and_tool_result_for_next_run():
    model = SequenceModel(
        [
            AssistantDecision(
                tool_calls=[ToolCall(id="weather-1", name="get_weather", arguments='{"city":"上海"}')]
            ),
            AssistantDecision(content="第一轮天气已查询"),
            AssistantDecision(content="第二轮使用了历史天气"),
        ]
    )
    conversation = Conversation()
    runner = AgentRunner(model, _registry([]))

    asyncio.run(runner.run("查询上海天气", conversation=conversation))
    asyncio.run(runner.run("根据刚才的天气回答", conversation=conversation))

    second_request = model.message_snapshots[2]
    assert [message["role"] for message in second_request] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
        "user",
    ]
    assert second_request[2]["tool_calls"][0]["id"] == "weather-1"
    assert second_request[3]["tool_call_id"] == "weather-1"
    assert second_request[4]["content"] == "第一轮天气已查询"


def test_conversations_are_isolated():
    model = SequenceModel(
        [
            AssistantDecision(content="会话 A"),
            AssistantDecision(content="会话 B"),
        ]
    )
    runner = AgentRunner(model, _registry([]))
    conversation_a = Conversation()
    conversation_b = Conversation()

    asyncio.run(runner.run("问题 A", conversation=conversation_a))
    asyncio.run(runner.run("问题 B", conversation=conversation_b))

    assert [message["content"] for message in model.message_snapshots[1]] == [
        conversation_b.messages[0]["content"],
        "问题 B",
    ]


def test_run_without_conversation_stays_stateless_between_calls():
    model = SequenceModel(
        [
            AssistantDecision(content="回答 A"),
            AssistantDecision(content="回答 B"),
        ]
    )
    runner = AgentRunner(model, _registry([]))

    asyncio.run(runner.run("问题 A"))
    asyncio.run(runner.run("问题 B"))

    assert [message["content"] for message in model.message_snapshots[1]] == [
        model.message_snapshots[1][0]["content"],
        "问题 B",
    ]
