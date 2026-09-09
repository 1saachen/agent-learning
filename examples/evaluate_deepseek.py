"""批量评估真实 DeepSeek：python -m examples.evaluate_deepseek"""

import asyncio

from phase2.client import OpenAIModelCaller
from phase2.evaluation import evaluate_cases, load_cases
from phase2.prompts import SYSTEM_PROMPT
from phase2.service import AnalysisService


async def main() -> None:
    service = AnalysisService(OpenAIModelCaller(SYSTEM_PROMPT))
    cases = load_cases("eval_cases.jsonl")
    summary = await evaluate_cases(cases, service.analyze)
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
