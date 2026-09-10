import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .contracts import CreateTodoArgs, GetWeatherArgs, SearchNotesArgs, ToolExecutionResult
from .tools.notes import DEFAULT_NOTES_DIR, search_notes
from .tools.base import PublicToolError
from .tools.todo import DEFAULT_TODO_STORE, create_todo
from .tools.weather import get_weather


ToolHandler = Callable[[BaseModel], Awaitable[dict[str, object] | list[dict[str, object]]]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler


@dataclass(frozen=True)
class PreparedToolCall:
    spec: ToolSpec
    args: BaseModel
    arguments: dict[str, Any]


class ToolRegistry:
    def __init__(self, specs: list[ToolSpec]):
        self._specs = {spec.name: spec for spec in specs}
        if len(self._specs) != len(specs):
            raise ValueError("工具名称不能重复")

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.args_model.model_json_schema(),
                },
            }
            for spec in self._specs.values()
        ]

    async def execute(
        self,
        name: str,
        raw_arguments: str,
    ) -> tuple[ToolExecutionResult, dict[str, Any]]:
        prepared, error = self.prepare(name, raw_arguments)
        if error is not None:
            return error, {}
        if prepared is None:
            raise RuntimeError("工具准备状态不一致")
        return await self.execute_prepared(prepared), prepared.arguments

    def prepare(
        self,
        name: str,
        raw_arguments: str,
    ) -> tuple[PreparedToolCall | None, ToolExecutionResult | None]:
        spec = self._specs.get(name)
        if spec is None:
            return None, ToolExecutionResult(
                ok=False,
                tool_name=name,
                error_type="unknown_tool",
                message="请求的工具不存在",
            )

        try:
            raw_data = json.loads(raw_arguments)
            if not isinstance(raw_data, dict):
                raise TypeError("工具参数必须是 JSON 对象")
            args = spec.args_model.model_validate(raw_data)
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            return None, ToolExecutionResult(
                ok=False,
                tool_name=name,
                error_type="invalid_arguments",
                message=_validation_message(exc),
            )

        validated = args.model_dump(mode="json")
        return PreparedToolCall(spec=spec, args=args, arguments=validated), None

    async def execute_prepared(self, prepared: PreparedToolCall) -> ToolExecutionResult:
        try:
            data = await prepared.spec.handler(prepared.args)
        except PublicToolError as exc:
            return ToolExecutionResult(
                ok=False,
                tool_name=prepared.spec.name,
                error_type="tool_execution_error",
                message=str(exc),
            )
        except Exception:
            return ToolExecutionResult(
                ok=False,
                tool_name=prepared.spec.name,
                error_type="tool_execution_error",
                message="工具执行失败",
            )
        return ToolExecutionResult(
            ok=True,
            tool_name=prepared.spec.name,
            data=data,
            message=_success_message(prepared.spec.name, data),
        )


def _validation_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        fields = sorted(
            {".".join(str(part) for part in error["loc"]) for error in exc.errors()}
        )
        return f"工具参数校验失败：{', '.join(fields)}"
    return "工具参数必须是合法的 JSON 对象"


def _success_message(
    tool_name: str,
    data: dict[str, object] | list[dict[str, object]],
) -> str:
    if tool_name == "get_weather" and isinstance(data, dict):
        return (
            f"天气：{data.get('location', '未知地点')}，"
            f"{data.get('temperature_c', '未知')} 摄氏度，"
            f"{data.get('weather', '未知天气')}"
        )[:300]
    if tool_name == "create_todo" and isinstance(data, dict):
        return (
            f"待办：{data.get('title', '未命名')}，"
            f"ID={data.get('id', '未知')}"
        )[:300]
    if tool_name == "search_notes" and isinstance(data, list):
        paths = [str(item.get("path", "")) for item in data[:5]]
        return f"笔记命中 {len(data)} 条：{', '.join(paths) or '无'}"[:300]
    return "工具执行成功"


def build_default_registry(
    *,
    notes_dir: Path = DEFAULT_NOTES_DIR,
    todo_store: Path = DEFAULT_TODO_STORE,
    weather_client: httpx.AsyncClient | None = None,
) -> ToolRegistry:
    async def notes_handler(args: BaseModel):
        return await search_notes(SearchNotesArgs.model_validate(args), notes_dir=notes_dir)

    async def todo_handler(args: BaseModel):
        return await create_todo(CreateTodoArgs.model_validate(args), store_path=todo_store)

    async def weather_handler(args: BaseModel):
        return await get_weather(GetWeatherArgs.model_validate(args), client=weather_client)

    return ToolRegistry(
        [
            ToolSpec(
                "search_notes",
                "搜索本地 Markdown 学习笔记，返回匹配文件、行号和文本片段。",
                SearchNotesArgs,
                notes_handler,
            ),
            ToolSpec(
                "create_todo",
                "在用户明确要求时创建本地待办事项。",
                CreateTodoArgs,
                todo_handler,
            ),
            ToolSpec(
                "get_weather",
                "查询指定城市当前的真实天气。",
                GetWeatherArgs,
                weather_handler,
            ),
        ]
    )
