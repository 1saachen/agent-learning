from datetime import date

import pytest
from pydantic import ValidationError

from stages.phase3_personal_agent.app.contracts import (
    CreateTodoArgs,
    GetWeatherArgs,
    SearchNotesArgs,
)


def test_create_todo_rejects_unknown_priority():
    with pytest.raises(ValidationError):
        CreateTodoArgs(title="复习 Tool Calling", priority="urgent")


def test_search_notes_limits_result_count():
    with pytest.raises(ValidationError):
        SearchNotesArgs(query="agent", max_results=100)


@pytest.mark.parametrize(
    ("model_type", "kwargs", "field"),
    [
        (SearchNotesArgs, {"query": "   "}, "query"),
        (CreateTodoArgs, {"title": "   "}, "title"),
        (GetWeatherArgs, {"city": "   "}, "city"),
    ],
)
def test_text_arguments_reject_whitespace_only(model_type, kwargs, field):
    with pytest.raises(ValidationError) as exc_info:
        model_type(**kwargs)

    assert field in str(exc_info.value)


def test_create_todo_normalizes_text_and_date():
    args = CreateTodoArgs(
        title="  出门带外套  ",
        due_date="2026-09-11",
        priority="high",
    )

    assert args.title == "出门带外套"
    assert args.due_date == date(2026, 9, 11)
    assert args.priority == "high"
