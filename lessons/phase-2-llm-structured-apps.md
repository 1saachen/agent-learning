# 第二阶段：LLM 与结构化应用

## 阶段目标

把“调用模型得到一段文字”升级为“得到可验证、可测试、可服务化的数据”。本阶段最终项目是简历分析助手。

## 课程地图

1. 模型调用：消息、参数、超时、重试和成本记录
2. Prompt：任务边界、Few-shot、拒答和版本化
3. 结构化输出：JSON Schema、Pydantic、验证失败恢复
4. 测试与评估：固定测试集、失败分类、质量和延迟指标
5. FastAPI 服务：请求/响应模型、流式输出和错误映射

## 第 1 课：最小可靠模型调用

### 概念

- `system` 消息定义行为边界，`user` 消息承载任务输入。
- `temperature` 越高通常越有变化；抽取类任务优先使用较低值。
- 网络调用必须设置 timeout；临时网络错误可以有限重试。
- 日志记录耗时、模型和请求 ID，不记录 API Key、完整简历或其他敏感原文。

### 环境准备

在 PowerShell 中执行：

```powershell
.\agent_env\Scripts\Activate.ps1
$env:LLM_BASE_URL = "https://your-compatible-endpoint/v1"
$env:LLM_API_KEY = "replace-me"
$env:LLM_MODEL = "your-model-name"
```

项目可以使用任何 OpenAI 兼容接口。没有 API Key 时，先完成下面的 mock 练习，不要把密钥写入代码或 Git。

### 练习 A：先定义输出契约

```python
from pydantic import BaseModel, Field

class ResumeAnalysis(BaseModel):
    candidate_summary: str = Field(min_length=1)
    matched_skills: list[str]
    missing_skills: list[str]
    match_score: float = Field(ge=0, le=1)
    interview_questions: list[str] = Field(min_length=1, max_length=10)
```

先写模型，再写 Prompt。这样模型返回什么不是“自由文本”，而是一个有边界的接口。

### 练习 B：实现解析函数

```python
import json
from pydantic import ValidationError

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
```

### 练习 C：用 mock 先跑通

```python
def mock_model(_: str) -> str:
    return '{"candidate_summary":"Python 后端候选人",' \
           '"matched_skills":["Python","FastAPI"],"missing_skills":["Docker"],' \
           '"match_score":0.78,"interview_questions":["如何设计异步 API？"]}'

result = parse_analysis(mock_model("分析简历"))
assert result.match_score == 0.78
```

### 今日任务

1. 在新文件 `phase2_exercise.py` 中实现 `ResumeAnalysis`、`parse_analysis` 和 `mock_model`。
2. 增加三个失败样例：非法 JSON、缺少 `match_score`、分数大于 1；分别断言抛出 `ValueError`。
3. 把 `ResumeAnalysis.model_json_schema()` 打印出来，观察它如何描述字段约束。
4. 用 pytest 运行测试，并把失败样例写进 README 或学习日志。

### 验收标准

- 正确数据能转换为 `ResumeAnalysis`。
- 非法 JSON 和字段校验错误不会静默通过。
- `match_score` 永远在 0 到 1 之间。
- 没有 API Key、简历原文等敏感信息进入源码或日志。

下一课会把 `mock_model` 替换成真实的 OpenAI 兼容 API 调用，并加入超时、有限重试和调用指标。

