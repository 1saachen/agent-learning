import json
from dataclasses import dataclass

from pydantic import ValidationError

from .client import ModelCaller, call_with_retry
from .contracts import ResumeAnalysis
from .prompts import build_analysis_prompt


@dataclass
class ParseFailure:
    kind: str
    message: str
    raw_preview: str


class AnalysisService:
    def __init__(self, caller: ModelCaller, *, max_attempts: int = 3):
        self.caller = caller
        self.max_attempts = max_attempts

    async def analyze(self, resume: str, job_description: str) -> ResumeAnalysis | ParseFailure:
        raw = await call_with_retry(
            self.caller,
            build_analysis_prompt(resume, job_description),
            max_attempts=self.max_attempts,
        )
        try:
            data = json.loads(raw)
            return ResumeAnalysis.model_validate(data)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            return ParseFailure("invalid_model_output", str(exc), raw[:200])
