import asyncio
from pathlib import Path

from pydantic import BaseModel, Field

from stages.phase3_personal_agent.app.registry import (
    ToolRegistry,
    ToolSpec,
    build_default_registry,
)


def test_registry_validates_arguments_before_execution():
    registry = build_default_registry()

    result, validated = asyncio.run(registry.execute("get_weather", '{"city": ""}'))

    assert result.ok is False
    assert result.error_type == "invalid_arguments"
    assert validated == {}


def test_registry_exports_openai_tool_schema():
    definition = next(
        item
        for item in build_default_registry().definitions()
        if item["function"]["name"] == "create_todo"
    )

    assert definition["type"] == "function"
    assert definition["function"]["parameters"]["properties"]["priority"]["enum"] == [
        "low",
        "medium",
        "high",
    ]


def test_registry_rejects_unknown_tool():
    result, validated = asyncio.run(ToolRegistry([]).execute("delete_all", "{}"))

    assert result.error_type == "unknown_tool"
    assert validated == {}


def test_registry_rejects_non_object_json():
    result, validated = asyncio.run(
        build_default_registry().execute("search_notes", '["agent"]')
    )

    assert result.error_type == "invalid_arguments"
    assert validated == {}


def test_default_registry_executes_real_notes_handler(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "guide.md").write_text("Agent 使用工具。", encoding="utf-8")
    registry = build_default_registry(notes_dir=notes)

    result, validated = asyncio.run(
        registry.execute("search_notes", '{"query":"agent","max_results":1}')
    )

    assert result.ok is True
    assert result.data[0]["path"] == "guide.md"
    assert validated == {"query": "agent", "max_results": 1}


class ExplodingArgs(BaseModel):
    value: int = Field(ge=0)


async def _explode(args: ExplodingArgs):
    raise RuntimeError(f"secret details: {args.value}")


def test_registry_converts_handler_exception_to_safe_result():
    registry = ToolRegistry(
        [ToolSpec("explode", "Always fails", ExplodingArgs, _explode)]
    )

    result, validated = asyncio.run(registry.execute("explode", '{"value":1}'))

    assert result.error_type == "tool_execution_error"
    assert result.message == "工具执行失败"
    assert "secret details" not in result.model_dump_json()
    assert validated == {"value": 1}
