"""真实 DeepSeek 调用示例。"""

import asyncio

from stages.phase2_resume_analysis.app.client import OpenAIModelCaller
from stages.phase2_resume_analysis.app.prompts import SYSTEM_PROMPT
from stages.phase2_resume_analysis.app.service import AnalysisService


async def main() -> None:
    service = AnalysisService(OpenAIModelCaller(SYSTEM_PROMPT))
    result = await service.analyze(
        "Python backend developer with FastAPI and PostgreSQL experience.",
        "Backend intern who should build Python APIs and learn Docker.",
    )
    print(result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else result)


if __name__ == "__main__":
    asyncio.run(main())
