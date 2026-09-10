"""离线运行的完整链路示例。"""

import asyncio

from stages.phase2_resume_analysis.app.client import FakeModelCaller
from stages.phase2_resume_analysis.app.service import AnalysisService


MOCK_RESPONSE = (
    '{"candidate_summary":"Python 后端候选人",'
    '"matched_skills":["Python","FastAPI"],"missing_skills":["Docker"],'
    '"match_score":0.78,"interview_questions":["如何设计异步 API？"],'
    '"years_of_experience":2}'
)


async def main() -> None:
    service = AnalysisService(FakeModelCaller(MOCK_RESPONSE))
    result = await service.analyze(
        "Python backend developer with FastAPI experience.",
        "Backend intern who can build APIs with Python and Docker.",
    )
    print(result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else result)


if __name__ == "__main__":
    asyncio.run(main())
