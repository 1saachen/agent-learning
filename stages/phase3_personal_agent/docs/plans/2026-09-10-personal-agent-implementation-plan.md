# Personal Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可真实调用 DeepSeek、搜索本地笔记、写入本地待办并查询 Open-Meteo 实时天气的单 Agent，同时提供可重复的离线测试和完整学习讲义。

**Architecture:** 使用原生 OpenAI 兼容 Tool Calling 协议。`AgentRunner` 只负责消息历史、步骤预算与重复调用保护；`ToolRegistry` 负责工具查找、Pydantic 参数校验与执行；工具实现只接触各自受控资源；`DeepSeekChatClient` 只负责供应商通信。模型和 HTTP 边界均可注入测试替身，真实命令行入口默认使用电脑环境变量中的 `DEEPSEEK_API_KEY`。

**Tech Stack:** Python 3.11+、Pydantic 2、OpenAI Python SDK、httpx、pytest、asyncio、Open-Meteo API

---

## File Map

| Path | Responsibility |
| --- | --- |
| `stages/phase3_personal_agent/app/contracts.py` | 工具参数、模型决策、工具结果、轨迹和 Agent 结果契约 |
| `stages/phase3_personal_agent/app/tools/notes.py` | 受限目录内 Markdown 笔记搜索 |
| `stages/phase3_personal_agent/app/tools/todo.py` | 原子写入 JSON 待办 |
| `stages/phase3_personal_agent/app/tools/weather.py` | Open-Meteo geocoding 与 current weather 查询 |
| `stages/phase3_personal_agent/app/registry.py` | 工具定义、Schema、参数校验与统一执行 |
| `stages/phase3_personal_agent/app/client.py` | DeepSeek Tool Calling 请求、响应归一化、网络重试 |
| `stages/phase3_personal_agent/app/prompts.py` | Agent System Prompt |
| `stages/phase3_personal_agent/app/agent.py` | 最多五步的 Agent 控制循环和重复调用保护 |
| `stages/phase3_personal_agent/examples/run_agent.py` | 真实命令行入口与 trace 展示 |
| `stages/phase3_personal_agent/tests/` | 契约、工具、注册表、客户端和循环的离线测试 |
| `stages/phase3_personal_agent/lesson.md` | 按代码阅读顺序编写的阶段三讲义 |
| `stages/phase3_personal_agent/docs/phase3-core-knowledge-guide.md` | Tool Calling、控制循环、安全与面试手册 |

### Task 1: Package Skeleton and Contracts

**Files:**
- Create: `stages/phase3_personal_agent/__init__.py`
- Create: `stages/phase3_personal_agent/app/__init__.py`
- Create: `stages/phase3_personal_agent/app/contracts.py`
- Create: `stages/phase3_personal_agent/tests/__init__.py`
- Create: `stages/phase3_personal_agent/tests/test_contracts.py`
- Create: `stages/phase3_personal_agent/requirements.txt`

- [ ] **Step 1: Write failing contract tests**

```python
from pydantic import ValidationError
import pytest

from stages.phase3_personal_agent.app.contracts import CreateTodoArgs, SearchNotesArgs


def test_create_todo_rejects_unknown_priority():
    with pytest.raises(ValidationError):
        CreateTodoArgs(title="复习 Tool Calling", priority="urgent")


def test_search_notes_limits_result_count():
    with pytest.raises(ValidationError):
        SearchNotesArgs(query="agent", max_results=100)
```

- [ ] **Step 2: Verify the tests fail because contracts do not exist**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_contracts.py -q`

Expected: collection fails with `ModuleNotFoundError`.

- [ ] **Step 3: Implement strict boundary models**

Create models with these exact public fields:

```python
class SearchNotesArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    max_results: int = Field(default=5, ge=1, le=10)

class CreateTodoArgs(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"

class GetWeatherArgs(BaseModel):
    city: str = Field(min_length=1, max_length=100)

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: str

class AssistantDecision(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)

class ToolExecutionResult(BaseModel):
    ok: bool
    tool_name: str
    data: dict[str, Any] | list[Any] | None = None
    error_type: str | None = None
    message: str

class TraceEntry(BaseModel):
    step: int
    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any]
    ok: bool
    summary: str
    duration_ms: float = Field(ge=0)

class AgentRunResult(BaseModel):
    answer: str
    stop_reason: Literal["completed", "max_steps_exceeded", "model_error"]
    steps: int = Field(ge=0)
    trace: list[TraceEntry] = Field(default_factory=list)
```

Use field validators to trim `query`, `title`, and `city`, rejecting whitespace-only input. Add `openai`, `httpx`, `pydantic`, and `pytest` to the stage requirements.

- [ ] **Step 4: Run the contract tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_contracts.py -q`

Expected: all contract tests pass.

- [ ] **Step 5: Commit only Task 1 paths**

```powershell
git add -- stages/phase3_personal_agent/__init__.py stages/phase3_personal_agent/app/__init__.py stages/phase3_personal_agent/app/contracts.py stages/phase3_personal_agent/tests/__init__.py stages/phase3_personal_agent/tests/test_contracts.py stages/phase3_personal_agent/requirements.txt
git commit --only -m "feat: add phase 3 agent contracts" -- stages/phase3_personal_agent/__init__.py stages/phase3_personal_agent/app/__init__.py stages/phase3_personal_agent/app/contracts.py stages/phase3_personal_agent/tests/__init__.py stages/phase3_personal_agent/tests/test_contracts.py stages/phase3_personal_agent/requirements.txt
```

### Task 2: Search Notes Tool

**Files:**
- Create: `stages/phase3_personal_agent/app/tools/__init__.py`
- Create: `stages/phase3_personal_agent/app/tools/notes.py`
- Create: `stages/phase3_personal_agent/data/notes/agent-basics.md`
- Create: `stages/phase3_personal_agent/tests/test_notes_tool.py`

- [ ] **Step 1: Write failing tests for matching and scope**

```python
@pytest.mark.asyncio
async def test_search_notes_returns_relative_path_line_and_snippet(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "guide.md").write_text("第一行\nTool Calling 将工具执行交给程序。\n", encoding="utf-8")
    result = await search_notes(SearchNotesArgs(query="tool calling"), notes_dir=notes)
    assert result[0]["path"] == "guide.md"
    assert result[0]["line"] == 2


@pytest.mark.asyncio
async def test_search_notes_ignores_non_markdown_files(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "secret.txt").write_text("Tool Calling", encoding="utf-8")
    assert await search_notes(SearchNotesArgs(query="Tool Calling"), notes_dir=notes) == []
```

- [ ] **Step 2: Run tests and observe the missing implementation failure**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_notes_tool.py -q`

Expected: import or missing function failure.

- [ ] **Step 3: Implement bounded case-insensitive search**

```python
async def search_notes(args: SearchNotesArgs, *, notes_dir: Path = DEFAULT_NOTES_DIR) -> list[dict[str, object]]:
    needle = args.query.casefold()
    matches: list[dict[str, object]] = []
    for path in sorted(notes_dir.glob("*.md")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if needle in line.casefold():
                matches.append({"path": path.name, "line": line_number, "snippet": line.strip()[:300]})
                if len(matches) >= args.max_results:
                    return matches
    return matches
```

The function never accepts a path from model arguments and only uses `glob("*.md")` in the injected fixed directory.

- [ ] **Step 4: Run notes tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_notes_tool.py -q`

Expected: all notes tests pass.

- [ ] **Step 5: Commit Task 2 paths**

```powershell
git add -- stages/phase3_personal_agent/app/tools/__init__.py stages/phase3_personal_agent/app/tools/notes.py stages/phase3_personal_agent/data/notes/agent-basics.md stages/phase3_personal_agent/tests/test_notes_tool.py
git commit --only -m "feat: add local notes search tool" -- stages/phase3_personal_agent/app/tools/__init__.py stages/phase3_personal_agent/app/tools/notes.py stages/phase3_personal_agent/data/notes/agent-basics.md stages/phase3_personal_agent/tests/test_notes_tool.py
```

### Task 3: Persistent Todo Tool

**Files:**
- Create: `stages/phase3_personal_agent/app/tools/todo.py`
- Create: `stages/phase3_personal_agent/data/todos.json`
- Create: `stages/phase3_personal_agent/tests/test_todo_tool.py`

- [ ] **Step 1: Write failing persistence tests**

```python
@pytest.mark.asyncio
async def test_create_todo_persists_normalized_item(tmp_path):
    store = tmp_path / "todos.json"
    store.write_text("[]", encoding="utf-8")
    item = await create_todo(CreateTodoArgs(title="  出门带外套  ", priority="high"), store_path=store)
    saved = json.loads(store.read_text(encoding="utf-8"))
    assert item["title"] == "出门带外套"
    assert item["id"] == saved[0]["id"]


@pytest.mark.asyncio
async def test_create_todo_does_not_replace_invalid_store(tmp_path):
    store = tmp_path / "todos.json"
    store.write_text('{"not": "a list"}', encoding="utf-8")
    with pytest.raises(TodoStoreError):
        await create_todo(CreateTodoArgs(title="测试"), store_path=store)
    assert store.read_text(encoding="utf-8") == '{"not": "a list"}'
```

- [ ] **Step 2: Verify failure before implementation**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_todo_tool.py -q`

Expected: missing module/function failure.

- [ ] **Step 3: Implement validated atomic JSON persistence**

Read the existing file as a JSON list, generate `uuid4().hex`, serialize `due_date` with `isoformat()`, and write the full list to a sibling temporary file using `NamedTemporaryFile(delete=False, dir=store_path.parent)`. Replace the target with `Path.replace()` only after the temporary write succeeds. Always clean up an unused temporary file in `finally`.

The stored item shape is:

```json
{
  "id": "program-generated-id",
  "title": "出门带外套",
  "due_date": null,
  "priority": "high",
  "completed": false,
  "created_at": "UTC ISO-8601 timestamp"
}
```

- [ ] **Step 4: Run todo tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_todo_tool.py -q`

Expected: all todo tests pass.

- [ ] **Step 5: Commit Task 3 paths**

```powershell
git add -- stages/phase3_personal_agent/app/tools/todo.py stages/phase3_personal_agent/data/todos.json stages/phase3_personal_agent/tests/test_todo_tool.py
git commit --only -m "feat: add persistent todo tool" -- stages/phase3_personal_agent/app/tools/todo.py stages/phase3_personal_agent/data/todos.json stages/phase3_personal_agent/tests/test_todo_tool.py
```

### Task 4: Open-Meteo Weather Tool

**Files:**
- Create: `stages/phase3_personal_agent/app/tools/weather.py`
- Create: `stages/phase3_personal_agent/tests/test_weather_tool.py`

- [ ] **Step 1: Write failing tests with controlled HTTP responses**

```python
@pytest.mark.asyncio
async def test_get_weather_combines_location_and_current_weather():
    transport = httpx.MockTransport(weather_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await get_weather(GetWeatherArgs(city="上海"), client=client)
    assert result["location"] == "Shanghai, China"
    assert result["temperature_c"] == 18.2
    assert result["weather"] == "阴"


@pytest.mark.asyncio
async def test_get_weather_rejects_missing_city_match():
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(WeatherToolError, match="没有找到城市"):
            await get_weather(GetWeatherArgs(city="不存在的城市"), client=client)
```

The handler returns a geocoding response for `/v1/search` and a current weather response for `/v1/forecast`.

- [ ] **Step 2: Verify weather tests fail before implementation**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_weather_tool.py -q`

Expected: missing implementation failure.

- [ ] **Step 3: Implement two-request weather lookup**

Use these endpoints and parameters:

```python
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

geocoding_params = {"name": args.city, "count": 1, "language": "zh", "format": "json"}
forecast_params = {
    "latitude": latitude,
    "longitude": longitude,
    "current": "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
    "timezone": "auto",
}
```

Call `response.raise_for_status()`, validate required response keys, and convert WMO codes through a program-owned mapping such as `0: "晴"`, `1: "大致晴朗"`, `2: "局部多云"`, `3: "阴"`, `61: "小雨"`, and a safe `"未知天气"` fallback. Convert `httpx.HTTPError`, malformed responses, and no result into `WeatherToolError` with user-safe messages. Create and close an internal `AsyncClient(timeout=10)` only when no client is injected.

- [ ] **Step 4: Run weather tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_weather_tool.py -q`

Expected: all weather tests pass.

- [ ] **Step 5: Commit Task 4 paths**

```powershell
git add -- stages/phase3_personal_agent/app/tools/weather.py stages/phase3_personal_agent/tests/test_weather_tool.py
git commit --only -m "feat: add Open-Meteo weather tool" -- stages/phase3_personal_agent/app/tools/weather.py stages/phase3_personal_agent/tests/test_weather_tool.py
```

### Task 5: Tool Registry and Schemas

**Files:**
- Create: `stages/phase3_personal_agent/app/registry.py`
- Create: `stages/phase3_personal_agent/tests/test_registry.py`

- [ ] **Step 1: Write failing registry tests**

```python
@pytest.mark.asyncio
async def test_registry_validates_arguments_before_execution():
    registry = build_default_registry()
    result, validated = await registry.execute("get_weather", '{"city": ""}')
    assert result.ok is False
    assert result.error_type == "invalid_arguments"
    assert validated == {}


def test_registry_exports_openai_tool_schema():
    definition = next(item for item in build_default_registry().definitions() if item["function"]["name"] == "create_todo")
    assert definition["type"] == "function"
    assert definition["function"]["parameters"]["properties"]["priority"]["enum"] == ["low", "medium", "high"]
```

- [ ] **Step 2: Run registry tests to confirm failure**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_registry.py -q`

Expected: missing registry failure.

- [ ] **Step 3: Implement registration, schema export, and guarded execution**

Define a `ToolSpec` containing `name`, `description`, `args_model`, and async `handler`. `ToolRegistry.definitions()` must return OpenAI-compatible function definitions generated by `args_model.model_json_schema()`. `execute(name, raw_arguments)` performs, in order:

```text
lookup name
  -> json.loads(raw_arguments)
  -> require JSON object
  -> args_model.model_validate(data)
  -> await handler(validated_args)
  -> ToolExecutionResult(ok=True, data=..., message=...)
```

Unknown tools return `unknown_tool`; JSON or Pydantic failures return `invalid_arguments`; handler exceptions return `tool_execution_error`. Return a tuple of the result and the safely validated argument dictionary for tracing. `build_default_registry()` wires the three real handlers and permits injecting notes/todo paths and an HTTP client in tests.

- [ ] **Step 4: Run registry and tool tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_registry.py stages\phase3_personal_agent\tests\test_*_tool.py -q`

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 5 paths**

```powershell
git add -- stages/phase3_personal_agent/app/registry.py stages/phase3_personal_agent/tests/test_registry.py
git commit --only -m "feat: add validated tool registry" -- stages/phase3_personal_agent/app/registry.py stages/phase3_personal_agent/tests/test_registry.py
```

### Task 6: DeepSeek Tool Calling Client

**Files:**
- Create: `stages/phase3_personal_agent/app/client.py`
- Create: `stages/phase3_personal_agent/tests/test_client.py`

- [ ] **Step 1: Write failing response-normalization and retry tests**

```python
@pytest.mark.asyncio
async def test_client_sends_tools_and_normalizes_tool_calls(monkeypatch):
    fake_sdk = FakeAsyncOpenAI(tool_call_response())
    monkeypatch.setattr(client_module, "_create_openai_client", lambda **kwargs: fake_sdk)
    client = DeepSeekChatClient(api_key="test-key", max_attempts=1)
    decision = await client.complete([{"role": "user", "content": "查天气"}], TOOL_DEFINITIONS)
    assert decision.tool_calls[0].name == "get_weather"
    assert fake_sdk.request["tool_choice"] == "auto"


def test_client_requires_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(ModelConfigurationError, match="DEEPSEEK_API_KEY"):
        DeepSeekChatClient()
```

- [ ] **Step 2: Run client tests and verify failure**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_client.py -q`

Expected: missing client failure.

- [ ] **Step 3: Implement the async model boundary**

Expose this protocol and class API:

```python
class ChatModel(Protocol):
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> AssistantDecision: ...

class DeepSeekChatClient:
    def __init__(self, *, api_key=None, base_url=None, model=None, timeout_seconds=30, max_attempts=3): ...
    async def complete(self, messages, tools) -> AssistantDecision: ...
```

Default to `DEEPSEEK_API_KEY`, `https://api.deepseek.com`, and `deepseek-v4-pro`. Send `model`, `messages`, `tools`, `tool_choice="auto"`, `temperature=0`, and timeout. Normalize `response.choices[0].message.content` and every SDK tool call's `id`, `function.name`, and `function.arguments` into `AssistantDecision`.

Retry only timeout, connection, rate-limit and 5xx-style failures, with bounded linear backoff. Authentication, permissions, invalid requests and missing API Key fail immediately through clear project exceptions.

- [ ] **Step 4: Run client tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_client.py -q`

Expected: all client tests pass.

- [ ] **Step 5: Commit Task 6 paths**

```powershell
git add -- stages/phase3_personal_agent/app/client.py stages/phase3_personal_agent/tests/test_client.py
git commit --only -m "feat: add DeepSeek tool calling client" -- stages/phase3_personal_agent/app/client.py stages/phase3_personal_agent/tests/test_client.py
```

### Task 7: Bounded Agent Loop

**Files:**
- Create: `stages/phase3_personal_agent/app/prompts.py`
- Create: `stages/phase3_personal_agent/app/agent.py`
- Create: `stages/phase3_personal_agent/tests/test_agent.py`

- [ ] **Step 1: Write failing loop tests**

The test-local `SequenceModel` and `RepeatingToolModel` are the project's Fake Model Client implementations. They provide deterministic `AssistantDecision` objects and never open a network connection.

```python
@pytest.mark.asyncio
async def test_agent_executes_tool_then_returns_final_answer():
    model = SequenceModel([
        AssistantDecision(tool_calls=[ToolCall(id="call-1", name="get_weather", arguments='{"city":"上海"}')]),
        AssistantDecision(content="上海当前 18.2 摄氏度。"),
    ])
    result = await AgentRunner(model, registry, max_steps=5).run("上海天气如何？")
    assert result.stop_reason == "completed"
    assert result.steps == 2
    assert result.trace[0].tool_name == "get_weather"
    assert model.messages[1][-1]["role"] == "tool"


@pytest.mark.asyncio
async def test_agent_blocks_duplicate_tool_call():
    same_call = ToolCall(id="call-1", name="create_todo", arguments='{"title":"带外套","priority":"high"}')
    model = SequenceModel([
        AssistantDecision(tool_calls=[same_call]),
        AssistantDecision(tool_calls=[same_call.model_copy(update={"id": "call-2"})]),
        AssistantDecision(content="待办已创建一次。"),
    ])
    result = await AgentRunner(model, registry).run("创建待办")
    assert [entry.ok for entry in result.trace] == [True, False]
    assert result.trace[1].summary == "duplicate_tool_call"


@pytest.mark.asyncio
async def test_agent_stops_at_max_steps():
    model = RepeatingToolModel()
    result = await AgentRunner(model, registry, max_steps=2).run("不断查天气")
    assert result.stop_reason == "max_steps_exceeded"
    assert result.steps == 2
```

- [ ] **Step 2: Run loop tests and observe failure**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_agent.py -q`

Expected: missing runner failure.

- [ ] **Step 3: Implement message-preserving AgentRunner**

Construct initial messages with `SYSTEM_PROMPT` and user input. For every model decision:

- append an Assistant message containing `content` and OpenAI-compatible `tool_calls`;
- return `completed` if no tool calls and content is non-empty;
- canonicalize valid JSON arguments with sorted keys, otherwise use the raw string;
- reject a repeated `(name, canonical_arguments)` before registry execution;
- measure each execution with `perf_counter()`;
- append a Tool message containing `tool_call_id`, `name`, and `result.model_dump_json()`;
- record a `TraceEntry` for every call;
- after `max_steps` model decisions, return `max_steps_exceeded` with a useful answer and the accumulated trace.

Model boundary exceptions return `model_error` while preserving existing trace. Validate `max_steps >= 1` in the constructor.

- [ ] **Step 4: Run Agent and registry tests**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_agent.py stages\phase3_personal_agent\tests\test_registry.py -q`

Expected: all selected tests pass.

- [ ] **Step 5: Commit Task 7 paths**

```powershell
git add -- stages/phase3_personal_agent/app/prompts.py stages/phase3_personal_agent/app/agent.py stages/phase3_personal_agent/tests/test_agent.py
git commit --only -m "feat: implement bounded agent loop" -- stages/phase3_personal_agent/app/prompts.py stages/phase3_personal_agent/app/agent.py stages/phase3_personal_agent/tests/test_agent.py
```

### Task 8: Real CLI, Sample Data, and Learning Documentation

**Files:**
- Create: `stages/phase3_personal_agent/examples/__init__.py`
- Create: `stages/phase3_personal_agent/examples/run_agent.py`
- Create: `stages/phase3_personal_agent/tests/test_cli.py`
- Create: `stages/phase3_personal_agent/README.md`
- Create: `stages/phase3_personal_agent/lesson.md`
- Create: `stages/phase3_personal_agent/docs/phase3-core-knowledge-guide.md`
- Modify: `README.md`
- Modify: `docs/project-memory.md`

- [ ] **Step 1: Add a CLI construction smoke test**

Test that `build_runner()` returns an `AgentRunner` when a test API key is supplied and that trace formatting includes step, tool, status, duration, and summary without including the key.

- [ ] **Step 2: Run the smoke test before adding the CLI**

Run: `.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_cli.py -q`

Expected: missing CLI module failure.

- [ ] **Step 3: Implement the real interactive entry point**

`run_agent.py` must:

```python
async def main() -> None:
    runner = build_runner()
    print("第三阶段个人研究助手。输入 exit 退出。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        result = await runner.run(user_input)
        print(f"\n助手：{result.answer}")
        print_trace(result.trace)

if __name__ == "__main__":
    asyncio.run(main())
```

`build_runner()` constructs the real DeepSeek client and default registry. Do not print or store the API Key.

- [ ] **Step 4: Write the learning materials**

The README gives installation, test, CLI, data location, example prompts, external API and safety notes. `lesson.md` teaches code in the order contracts -> tools -> registry -> client -> loop -> trace. The core guide covers Tool Calling protocol, JSON Schema, `tool_call_id`, multiple calls, parameter validation, permissions, timeout, idempotency, repeated calls, max steps, observability, testing probabilistic systems, and interview questions.

Update root README and project memory with the phase-three path, current status, exact run command, DeepSeek/Open-Meteo configuration, and the rule that `data/todos.json` contains local runtime data.

- [ ] **Step 5: Run CLI smoke tests and documentation checks**

Run:

```powershell
.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent\tests\test_cli.py -q
rg -n "Tool Calling|tool_call_id|最大步骤|参数校验|幂等|DeepSeek|Open-Meteo" stages\phase3_personal_agent\lesson.md stages\phase3_personal_agent\docs\phase3-core-knowledge-guide.md
```

Expected: smoke tests pass and every required topic has at least one meaningful occurrence.

- [ ] **Step 6: Commit Task 8 paths without absorbing unrelated worktree changes**

Review and commit these paths explicitly because root README and project memory already contain user changes that must be preserved:

```powershell
git diff -- README.md docs/project-memory.md stages/phase3_personal_agent/examples/__init__.py stages/phase3_personal_agent/examples/run_agent.py stages/phase3_personal_agent/tests/test_cli.py stages/phase3_personal_agent/README.md stages/phase3_personal_agent/lesson.md stages/phase3_personal_agent/docs/phase3-core-knowledge-guide.md
git add -- README.md docs/project-memory.md stages/phase3_personal_agent/examples/__init__.py stages/phase3_personal_agent/examples/run_agent.py stages/phase3_personal_agent/tests/test_cli.py stages/phase3_personal_agent/README.md stages/phase3_personal_agent/lesson.md stages/phase3_personal_agent/docs/phase3-core-knowledge-guide.md
git commit --only -m "docs: add phase 3 learning experience" -- README.md docs/project-memory.md stages/phase3_personal_agent/examples/__init__.py stages/phase3_personal_agent/examples/run_agent.py stages/phase3_personal_agent/tests/test_cli.py stages/phase3_personal_agent/README.md stages/phase3_personal_agent/lesson.md stages/phase3_personal_agent/docs/phase3-core-knowledge-guide.md
```

### Task 9: Full Verification and Real Integration Probe

**Files:**
- Modify only files whose verification reveals a concrete defect.

- [ ] **Step 1: Install stage dependencies**

Run: `.\agent_env\Scripts\python.exe -m pip install -r stages\phase3_personal_agent\requirements.txt`

Expected: exit code 0.

- [ ] **Step 2: Run all offline tests**

Run: `.\agent_env\Scripts\python.exe -m pytest -q`

Expected: all phase-two and phase-three tests pass with zero failures.

- [ ] **Step 3: Run static repository checks**

Run:

```powershell
git diff --check
rg -n "TO[D]O|TB[D]" stages\phase3_personal_agent
```

Expected: no whitespace errors and no unfinished placeholders.

- [ ] **Step 4: Probe the real weather tool directly**

Run a small Python command that awaits `get_weather(GetWeatherArgs(city="上海"))` and prints only the normalized result.

Expected: a result containing location, local time, temperature, apparent temperature, precipitation, weather description, weather code, and wind speed. If network access is unavailable, report the exact external error without treating offline unit tests as failed.

- [ ] **Step 5: Probe the real DeepSeek Agent**

Run the module and submit:

```text
查看上海现在的天气。如果温度低于 20 摄氏度，创建一个标题为“出门带外套”的高优先级待办；否则只告诉我天气。
```

Expected: DeepSeek calls `get_weather`; it conditionally calls `create_todo`; the final response matches actual tool results; trace shows the complete path. This request may incur DeepSeek API cost and must not print credentials.

- [ ] **Step 6: Inspect local side effects**

If the temperature condition caused a todo, inspect `data/todos.json` and verify exactly one new item was created. Confirm duplicate protection prevented repeated writes.

- [ ] **Step 7: Record verification evidence**

Update the stage README only if the observed real provider behavior requires a compatibility note. Report test count, external probe status, and any warning accurately.

---

## Completion Checklist

- [ ] All three real tools run through the registry.
- [ ] Every model-provided argument is validated before execution.
- [ ] Tool results use matching `tool_call_id` messages.
- [ ] Duplicate calls do not repeat side effects.
- [ ] Five-step maximum is enforced.
- [ ] Trace records each tool execution without secrets.
- [ ] Real CLI reads the existing system API Key.
- [ ] Offline tests do not call DeepSeek or Open-Meteo.
- [ ] Full repository tests pass.
- [ ] README, lesson, core guide, and project memory are current.
