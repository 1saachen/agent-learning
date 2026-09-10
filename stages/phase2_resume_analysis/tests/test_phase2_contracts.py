import pytest
from pydantic import ValidationError

from stages.phase2_resume_analysis.app.contracts import ResumeAnalysis, ResumeRequest


def test_resume_analysis_accepts_valid_data():
    result = ResumeAnalysis(
        candidate_summary="Python backend developer",
        matched_skills=["Python"],
        missing_skills=["Docker"],
        match_score=0.8,
        interview_questions=["How do you test APIs?"],
        years_of_experience=2,
    )
    assert result.match_score == 0.8


def test_resume_analysis_rejects_out_of_range_score():
    with pytest.raises(ValidationError):
        ResumeAnalysis(
            candidate_summary="x", matched_skills=[], missing_skills=[],
            match_score=1.1, interview_questions=["q"],
        )


def test_resume_request_rejects_short_text():
    with pytest.raises(ValidationError):
        ResumeRequest(resume="short", job_description="short")
