"""第二阶段第 1 课：结构化模型输出练习。"""

import json
import os
from openai import AsyncOpenAI
import asyncio
from pydantic import BaseModel, Field, ValidationError
from phase2.prompts import SYSTEM_PROMPT


class ResumeAnalysis(BaseModel):
    candidate_summary: str = Field(min_length=1)
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float = Field(ge=0, le=1)
    interview_questions: list[str] = Field(min_length=1, max_length=10)
    years_of_experience: int = Field(default=0, ge=0)


def parse_analysis(raw: str) -> ResumeAnalysis:
    """将模型文本解析为经过约束的业务对象。"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("模型返回的不是合法 JSON") from exc

    try:
        return ResumeAnalysis.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"模型输出不符合契约: {exc}") from exc


def mock_model(_: str) -> str:
    """用固定结果模拟模型，避免第一课依赖 API Key。"""
    return (
        '{"candidate_summary":"Python 后端候选人",'
        '"matched_skills":["Python","FastAPI"],'
        '"missing_skills":["Docker"],"match_score":0.78,'
        '"interview_questions":["如何设计异步 API？"]}'
    )

client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

async def call_model(user_prompt: str) -> str:
    """调用 DeepSeek API 获取模型输出。"""
    response = await client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        response_format={"type": "json_object"},
        timeout=30,
    )
    return response.choices[0].message.content or ""

async def main():
    raw = await call_model(
        "我是小明，我有 3 年 Python 后端开发经验，"
        "熟悉 FastAPI 和 Docker。请帮我分析我的简历。"
    )

    result = parse_analysis(raw)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
