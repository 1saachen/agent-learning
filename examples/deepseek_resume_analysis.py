"""真实 DeepSeek 调用：python -m examples.deepseek_resume_analysis"""

import asyncio

from phase2.client import OpenAIModelCaller
from phase2.prompts import SYSTEM_PROMPT
from phase2.service import AnalysisService


async def main() -> None:
    service = AnalysisService(OpenAIModelCaller(SYSTEM_PROMPT))
    result = await service.analyze(
        "Python backend developer with FastAPI and PostgreSQL experience.",
        "Backend intern who should build Python APIs and learn Docker.",
    )
    print(result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else result)


if __name__ == "__main__":
    asyncio.run(main())
