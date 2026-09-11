import asyncio

from stages.phase3_personal_agent.app.agent import AgentRunner
from stages.phase3_personal_agent.app.contracts import TraceEntry
from stages.phase3_personal_agent.examples import run_agent


class StubClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_build_runner_uses_supplied_api_key(monkeypatch):
    monkeypatch.setattr(run_agent, "DeepSeekChatClient", StubClient)

    runner = run_agent.build_runner(api_key="private-test-key")

    assert isinstance(runner, AgentRunner)
    assert runner.model.kwargs["api_key"] == "private-test-key"


def test_print_trace_shows_execution_without_credentials(capsys):
    trace = [
        TraceEntry(
            step=1,
            tool_call_id="call-1",
            tool_name="get_weather",
            arguments={"city": "上海"},
            ok=True,
            summary="工具执行成功",
            duration_ms=12.34,
        )
    ]

    run_agent.print_trace(trace)
    output = capsys.readouterr().out

    assert "步骤 1" in output
    assert "get_weather" in output
    assert "成功" in output
    assert "12.34 ms" in output
    assert "private-test-key" not in output


def test_interactive_cli_reuses_one_conversation(monkeypatch):
    runner = object()
    inputs = iter(["第一轮", "第二轮", "exit"])
    calls = []

    monkeypatch.setattr(run_agent, "build_runner", lambda: runner)
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    async def record_run(actual_runner, user_input, *, conversation=None):
        calls.append((actual_runner, user_input, conversation))

    monkeypatch.setattr(run_agent, "_run_once", record_run)

    asyncio.run(run_agent.main())

    assert [call[1] for call in calls] == ["第一轮", "第二轮"]
    assert calls[0][0] is runner
    assert calls[0][2] is calls[1][2]
