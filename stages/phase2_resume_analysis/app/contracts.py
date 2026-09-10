from pydantic import BaseModel, Field


class ResumeAnalysis(BaseModel):
    candidate_summary: str = Field(min_length=1)
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float = Field(ge=0, le=1)
    interview_questions: list[str] = Field(min_length=1, max_length=10)
    years_of_experience: int = Field(default=0, ge=0)


class ResumeRequest(BaseModel):
    resume: str = Field(min_length=20, max_length=20_000)
    job_description: str = Field(min_length=20, max_length=20_000)
