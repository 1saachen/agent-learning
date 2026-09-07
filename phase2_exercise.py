"""第二阶段第 1 课：结构化模型输出练习。"""

import json

from pydantic import BaseModel, Field, ValidationError


class ResumeAnalysis(BaseModel):
    candidate_summary: str = Field(min_length=1)
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float = Field(ge=0, le=1)
    interview_questions: list[str] = Field(min_length=1, max_length=10)


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


if __name__ == "__main__":
    result = parse_analysis(mock_model("分析简历"))
    print(result.model_dump_json(indent=2))
