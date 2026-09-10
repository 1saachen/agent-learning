import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from ..contracts import CreateTodoArgs
from .base import PublicToolError


DEFAULT_TODO_STORE = Path(__file__).resolve().parents[2] / "data" / "todos.json"


class TodoStoreError(PublicToolError):
    """待办文件不能被安全读取或写入。"""


def _load_todos(store_path: Path) -> list[object]:
    if not store_path.exists():
        return []
    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TodoStoreError("待办文件无法解析，未执行写入") from exc
    except OSError as exc:
        raise TodoStoreError("待办文件无法读取") from exc
    if not isinstance(data, list):
        raise TodoStoreError("待办文件必须是 JSON 数组，未执行写入")
    return data


def _atomic_write(store_path: Path, todos: list[object]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=store_path.parent,
            prefix=f".{store_path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            json.dump(todos, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
            temp_path = Path(temp_file.name)
        temp_path.replace(store_path)
        temp_path = None
    except OSError as exc:
        raise TodoStoreError("待办文件写入失败") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


async def create_todo(
    args: CreateTodoArgs,
    *,
    store_path: Path = DEFAULT_TODO_STORE,
) -> dict[str, object]:
    todos = _load_todos(store_path)
    item: dict[str, object] = {
        "id": uuid4().hex,
        "title": args.title,
        "due_date": args.due_date.isoformat() if args.due_date else None,
        "priority": args.priority,
        "completed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    todos.append(item)
    _atomic_write(store_path, todos)
    return item
