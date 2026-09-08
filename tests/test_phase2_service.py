import asyncio
import pytest

from phase2.client import FakeModelCaller, ModelCallError
from phase2.service import AnalysisService, ParseFailure


VALID = '{"candidate_summary":"backend","matched_skills":["Python"],"missing_skills":[],' \
        '"match_score":0.7,"interview_questions":["q"],"years_of_experience":2}'


def test_service_returns_structured_analysis():
    service = AnalysisService(FakeModelCaller(VALID))
    result = asyncio.run(service.analyze("a resume that is long enough", "a job description that is long enough"))
    assert result.match_score == 0.7


def test_service_returns_diagnostic_for_bad_json():
    service = AnalysisService(FakeModelCaller("bad"))
    result = asyncio.run(service.analyze("resume", "job"))
    assert isinstance(result, ParseFailure)
    assert result.kind == "invalid_model_output"


def test_service_propagates_model_failure():
    class Failing:
        async def __call__(self, _: str) -> str:
            raise ModelCallError("down")

    with pytest.raises(ModelCallError):
        asyncio.run(AnalysisService(Failing()).analyze("resume", "job"))
