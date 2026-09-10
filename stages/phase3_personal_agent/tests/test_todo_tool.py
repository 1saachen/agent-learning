import asyncio
import json

import pytest

from stages.phase3_personal_agent.app.contracts import CreateTodoArgs
from stages.phase3_personal_agent.app.tools.todo import TodoStoreError, create_todo


def test_create_todo_persists_normalized_item(tmp_path):
    store = tmp_path / "todos.json"
    store.write_text("[]", encoding="utf-8")

    item = asyncio.run(
        create_todo(
            CreateTodoArgs(
                title="  出门带外套  ",
                due_date="2026-09-11",
                priority="high",
            ),
            store_path=store,
        )
    )
    saved = json.loads(store.read_text(encoding="utf-8"))

    assert item["title"] == "出门带外套"
    assert item["due_date"] == "2026-09-11"
    assert item["completed"] is False
    assert item["id"] == saved[0]["id"]
    assert item["created_at"].endswith("+00:00")


def test_create_todo_generates_unique_ids(tmp_path):
    store = tmp_path / "todos.json"
    store.write_text("[]", encoding="utf-8")

    first = asyncio.run(create_todo(CreateTodoArgs(title="任务一"), store_path=store))
    second = asyncio.run(create_todo(CreateTodoArgs(title="任务二"), store_path=store))

    assert first["id"] != second["id"]
    assert len(json.loads(store.read_text(encoding="utf-8"))) == 2


def test_create_todo_initializes_missing_store(tmp_path):
    store = tmp_path / "nested" / "todos.json"

    item = asyncio.run(create_todo(CreateTodoArgs(title="测试"), store_path=store))

    assert json.loads(store.read_text(encoding="utf-8"))[0]["id"] == item["id"]


def test_create_todo_does_not_replace_invalid_store(tmp_path):
    store = tmp_path / "todos.json"
    original = '{"not": "a list"}'
    store.write_text(original, encoding="utf-8")

    with pytest.raises(TodoStoreError, match="JSON 数组"):
        asyncio.run(create_todo(CreateTodoArgs(title="测试"), store_path=store))

    assert store.read_text(encoding="utf-8") == original


def test_create_todo_does_not_replace_malformed_json(tmp_path):
    store = tmp_path / "todos.json"
    original = "[broken"
    store.write_text(original, encoding="utf-8")

    with pytest.raises(TodoStoreError, match="无法解析"):
        asyncio.run(create_todo(CreateTodoArgs(title="测试"), store_path=store))

    assert store.read_text(encoding="utf-8") == original
