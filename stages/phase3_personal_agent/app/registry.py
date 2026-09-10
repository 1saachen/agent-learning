import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from .contracts import CreateTodoArgs, GetWeatherArgs, SearchNotesArgs, ToolExecutionResult
from .tools.notes import DEFAULT_NOTES_DIR, search_notes
from .tools.todo import DEFAULT_TODO_STORE, create_todo
from .tools.weather import get_weather


ToolHandler = Callable[[BaseModel], Awaitable[dict[str, object] | list[dict[str, object]]]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler


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
        spec = self._specs.get(name)
        if spec is None:
            return (
                ToolExecutionResult(
                    ok=False,
                    tool_name=name,
                    error_type="unknown_tool",
                    message="请求的工具不存在",
                ),
                {},
            )

        try:
            raw_data = json.loads(raw_arguments)
            if not isinstance(raw_data, dict):
                raise TypeError("工具参数必须是 JSON 对象")
            args = spec.args_model.model_validate(raw_data)
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            return (
                ToolExecutionResult(
                    ok=False,
                    tool_name=name,
                    error_type="invalid_arguments",
                    message=_validation_message(exc),
                ),
                {},
            )

        validated = args.model_dump(mode="json")
        try:
            data = await spec.handler(args)
        except Exception:
            return (
                ToolExecutionResult(
                    ok=False,
                    tool_name=name,
                    error_type="tool_execution_error",
                    message="工具执行失败",
                ),
                validated,
            )
        return (
            ToolExecutionResult(
                ok=True,
                tool_name=name,
                data=data,
                message="工具执行成功",
            ),
            validated,
        )


def _validation_message(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        fields = sorted(
            {".".join(str(part) for part in error["loc"]) for error in exc.errors()}
        )
        return f"工具参数校验失败：{', '.join(fields)}"
    return "工具参数必须是合法的 JSON 对象"


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
