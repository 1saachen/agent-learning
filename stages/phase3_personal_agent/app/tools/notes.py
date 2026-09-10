from pathlib import Path

from ..contracts import SearchNotesArgs


DEFAULT_NOTES_DIR = Path(__file__).resolve().parents[2] / "data" / "notes"


async def search_notes(
    args: SearchNotesArgs,
    *,
    notes_dir: Path = DEFAULT_NOTES_DIR,
) -> list[dict[str, object]]:
    if not notes_dir.is_dir():
        return []

    needle = args.query.casefold()
    matches: list[dict[str, object]] = []
    for path in sorted(notes_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if needle not in line.casefold():
                continue
            matches.append(
                {
                    "path": path.name,
                    "line": line_number,
                    "snippet": line.strip()[:300],
                }
            )
            if len(matches) >= args.max_results:
                return matches
    return matches
