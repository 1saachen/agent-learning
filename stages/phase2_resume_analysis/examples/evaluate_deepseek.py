"""批量评估真实 DeepSeek。"""

import asyncio
from pathlib import Path

from stages.phase2_resume_analysis.app.client import OpenAIModelCaller
from stages.phase2_resume_analysis.app.evaluation import evaluate_cases, load_cases
from stages.phase2_resume_analysis.app.prompts import SYSTEM_PROMPT
from stages.phase2_resume_analysis.app.service import AnalysisService


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "eval_cases.jsonl"


async def main() -> None:
    service = AnalysisService(OpenAIModelCaller(SYSTEM_PROMPT))
    cases = load_cases(DATA_PATH)
    summary = await evaluate_cases(cases, service.analyze)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
