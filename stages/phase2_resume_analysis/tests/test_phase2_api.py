from fastapi.testclient import TestClient

from stages.phase2_resume_analysis.app.api import create_app
from stages.phase2_resume_analysis.app.client import FakeModelCaller, ModelCallError


VALID = '{"candidate_summary":"backend","matched_skills":["Python"],"missing_skills":[],' \
        '"match_score":0.7,"interview_questions":["q"],"years_of_experience":2}'


def test_api_returns_analysis():
    client = TestClient(create_app(FakeModelCaller(VALID)))
    response = client.post("/resume/analyze", json={"resume": "a" * 20, "job_description": "b" * 20})
    assert response.status_code == 200
    assert response.json()["match_score"] == 0.7


def test_api_rejects_short_request():
    client = TestClient(create_app(FakeModelCaller(VALID)))
    response = client.post("/resume/analyze", json={"resume": "short", "job_description": "short"})
    assert response.status_code == 422


def test_api_maps_parse_failure_to_502():
    client = TestClient(create_app(FakeModelCaller("bad")))
    response = client.post("/resume/analyze", json={"resume": "a" * 20, "job_description": "b" * 20})
    assert response.status_code == 502


def test_api_maps_model_failure_to_504():
    class Failing:
        async def __call__(self, _: str) -> str:
            raise ModelCallError("down")

    client = TestClient(create_app(Failing()))
    response = client.post("/resume/analyze", json={"resume": "a" * 20, "job_description": "b" * 20})
    assert response.status_code == 504
