import asyncio

from stages.phase3_personal_agent.app.contracts import SearchNotesArgs
from stages.phase3_personal_agent.app.tools.notes import search_notes


def test_search_notes_returns_relative_path_line_and_snippet(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "guide.md").write_text(
        "第一行\nTool Calling 将工具执行交给程序。\n",
        encoding="utf-8",
    )

    result = asyncio.run(
        search_notes(SearchNotesArgs(query="tool calling"), notes_dir=notes)
    )

    assert result == [
        {
            "path": "guide.md",
            "line": 2,
            "snippet": "Tool Calling 将工具执行交给程序。",
        }
    ]


def test_search_notes_ignores_non_markdown_files(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "secret.txt").write_text("Tool Calling", encoding="utf-8")

    result = asyncio.run(
        search_notes(SearchNotesArgs(query="Tool Calling"), notes_dir=notes)
    )

    assert result == []


def test_search_notes_honors_max_results(tmp_path):
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "guide.md").write_text("agent one\nagent two\n", encoding="utf-8")

    result = asyncio.run(
        search_notes(
            SearchNotesArgs(query="agent", max_results=1),
            notes_dir=notes,
        )
    )

    assert len(result) == 1


def test_search_notes_returns_empty_when_notes_directory_is_missing(tmp_path):
    result = asyncio.run(
        search_notes(
            SearchNotesArgs(query="agent"),
            notes_dir=tmp_path / "missing",
        )
    )

    assert result == []
