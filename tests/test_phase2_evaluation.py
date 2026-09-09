import asyncio
import json

from phase2.contracts import ResumeAnalysis
from phase2.evaluation import evaluate_cases, load_cases, skill_hit_rate


def test_load_cases_reads_jsonl(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(json.dumps({"resume": "r", "job_description": "j", "expected_skills": ["Python"]}) + "\n")
    cases = load_cases(path)
    assert cases[0].expected_skills == ["Python"]


def test_skill_hit_rate_is_case_insensitive():
    result = ResumeAnalysis(
        candidate_summary="x", matched_skills=["python", "FastAPI"],
        missing_skills=[], match_score=0.8, interview_questions=["q"],
    )
    assert skill_hit_rate(result, ["Python", "Docker"]) == 0.5


def test_evaluate_cases_aggregates_success_and_skill_rate():
    async def analyzer(_: str, __: str):
        return ResumeAnalysis(
            candidate_summary="x", matched_skills=["Python"],
            missing_skills=[], match_score=0.8, interview_questions=["q"],
        )

    cases = [{"resume": "r", "job_description": "j", "expected_skills": ["Python", "Docker"]}]
    summary = asyncio.run(evaluate_cases(cases, analyzer))
    assert summary.total_cases == 1
    assert summary.successful_cases == 1
    assert summary.skill_hit_rate == 0.5
