import json
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from .contracts import ResumeAnalysis


@dataclass(frozen=True)
class EvaluationCase:
    resume: str
    job_description: str
    expected_skills: list[str]


@dataclass(frozen=True)
class EvaluationSummary:
    total_cases: int
    successful_cases: int
    failed_cases: int
    skill_hit_rate: float
    average_match_score: float


def load_cases(path: str | Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            cases.append(EvaluationCase(
                resume=data["resume"],
                job_description=data["job_description"],
                expected_skills=data.get("expected_skills", []),
            ))
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"评估样例第 {line_number} 行格式错误") from exc
    return cases


def skill_hit_rate(result: ResumeAnalysis, expected_skills: Iterable[str]) -> float:
    expected = {skill.strip().casefold() for skill in expected_skills if skill.strip()}
    if not expected:
        return 1.0
    matched = {skill.strip().casefold() for skill in result.matched_skills}
    return len(expected & matched) / len(expected)


async def evaluate_cases(
    cases: Iterable[EvaluationCase | dict],
    analyzer: Callable[[str, str], Awaitable[object]],
) -> EvaluationSummary:
    total = successful = failed = 0
    rates: list[float] = []
    scores: list[float] = []
    for case in cases:
        if isinstance(case, dict):
            case = EvaluationCase(**case)
        total += 1
        result = await analyzer(case.resume, case.job_description)
        if not isinstance(result, ResumeAnalysis):
            failed += 1
            continue
        successful += 1
        rates.append(skill_hit_rate(result, case.expected_skills))
        scores.append(result.match_score)
    return EvaluationSummary(
        total_cases=total,
        successful_cases=successful,
        failed_cases=failed,
        skill_hit_rate=sum(rates) / len(rates) if rates else 0.0,
        average_match_score=sum(scores) / len(scores) if scores else 0.0,
    )
