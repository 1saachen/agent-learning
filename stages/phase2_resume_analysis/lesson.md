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

客户端会自动读取电脑环境变量 `DEEPSEEK_API_KEY`，不需要在每次运行前执行 PowerShell 设置命令。DeepSeek OpenAI 兼容接口的默认地址是 `https://api.deepseek.com`，默认模型是 `deepseek-v4-pro`。`LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_USE_RESPONSE_FORMAT` 仅用于你已经在系统环境变量中配置覆盖值的场景。

项目默认使用 DeepSeek 的 OpenAI 兼容接口，也可以替换为其他兼容供应商。没有 API Key 时，先完成下面的 mock 练习，不要把密钥写入代码或 Git。

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

1. 在 `exercises/phase2_exercise.py` 中实现 `ResumeAnalysis`、`parse_analysis` 和 `mock_model`。
2. 增加三个失败样例：非法 JSON、缺少 `match_score`、分数大于 1；分别断言抛出 `ValueError`。
3. 把 `ResumeAnalysis.model_json_schema()` 打印出来，观察它如何描述字段约束。
4. 用 pytest 运行测试，并把失败样例写进 README 或学习日志。

### 验收标准

- 正确数据能转换为 `ResumeAnalysis`。
- 非法 JSON 和字段校验错误不会静默通过。
- `match_score` 永远在 0 到 1 之间。
- 没有 API Key、简历原文等敏感信息进入源码或日志。

下一课会把 `mock_model` 替换成真实的 OpenAI 兼容 API 调用，并加入超时、有限重试和调用指标。

## 第 2 课：Prompt 设计与真实模型调用

### 目标

让模型稳定理解任务边界，并通过一个可替换的客户端调用真实 OpenAI 兼容 API。业务代码不应该到处散落 Prompt 和 API Key。

### Prompt 模板

```python
from stages.phase2_resume_analysis.app.prompts import SYSTEM_PROMPT

# SYSTEM_PROMPT 已包含完整字段契约、拒绝替代字段的规则和 Few-shot 示例。

def build_prompt(resume: str, job_description: str) -> str:
    return f"简历：\\n{resume}\\n\\n职位描述：\\n{job_description}"
```

不要把不可信的简历内容拼到 system 指令中。把简历放在 user 消息，并明确告诉模型它是待分析数据，避免简历中的指令覆盖系统规则。

### API 客户端骨架

```python
import os
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
)

async def call_model(user_prompt: str) -> str:
    response = await client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "deepseek-v4-pro"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        timeout=30,
    )
    return response.choices[0].message.content or ""
```

安装 SDK：`.\agent_env\Scripts\python.exe -m pip install openai`。不同供应商对 `response_format` 的支持可能不同；不支持时保留 Prompt 约束，并继续使用本地 Pydantic 校验。

### 重试原则

只对超时、连接错误和明确的临时服务端错误重试，最多 2 次，并使用递增等待。不要对参数错误或验证错误无限重试。生产代码还应记录请求 ID、模型、耗时和 token 用量，不记录密钥和完整用户文本。

### 练习

1. 把 `mock_model` 替换为一个可注入的 `model_call` 函数，测试时仍传入 mock。
2. 增加 `resume`、`job_description` 两个输入，Prompt 中明确“只根据提供内容”。
3. 模拟一次超时，确认函数最多重试 2 次后抛出异常。
4. 使用环境变量运行一次真实请求，并检查日志中没有简历原文。

### 验收

- API Key 只从环境变量读取。
- Prompt 与业务函数分离且可版本化。
- 超时和临时错误有有限重试。
- 真实客户端可以被 mock 替换，单元测试不依赖网络。

## 第 3 课：结构化输出与验证恢复

### 三层防线

1. **模型约束**：JSON Schema 或 `response_format`。
2. **解析约束**：`json.loads`，拒绝 Markdown 围栏和截断文本。
3. **业务约束**：Pydantic 字段、范围、长度和枚举校验。

模型输出不可信，永远不能直接写入数据库或执行工具。

### 可诊断的解析结果

```python
from dataclasses import dataclass

@dataclass
class ParseFailure:
    kind: str
    message: str
    raw_preview: str

def parse_with_diagnostics(raw: str) -> ResumeAnalysis | ParseFailure:
    try:
        return parse_analysis(raw)
    except ValueError as exc:
        return ParseFailure("invalid_model_output", str(exc), raw[:200])
```

重试时不要盲目重复同一个 Prompt。把校验错误转成简短的修复指令，例如“字段 `match_score` 必须是 0 到 1 的数字”，并把原始任务和错误一起发送；仍失败则返回明确错误，让上层决定降级或人工处理。

### 练习

1. 增加 `years_of_experience`、技能去重和问题数量限制。
2. 处理模型返回的 Markdown `json` 代码围栏：先记录为失败，或实现一个严格、有限的清理函数并测试边界。
3. 设计 `ParseFailure`，让 API 可以区分模型错误、网络错误和用户输入错误。

### 常见错误

- 只用正则表达式从任意文本中“抠 JSON”；
- 为了让测试通过而放宽所有字段；
- 验证失败后无限调用模型；
- 把模型的自然语言解释当成结构化字段。

## 第 4 课：测试与评估

### 测试分层

- **单元测试**：测试 Prompt 构造、JSON 解析、Pydantic 校验和重试决策。
- **契约测试**：用固定 mock 响应验证客户端适配器。
- **离线评估**：准备 10-30 条简历/职位样例，检查字段正确性和边界案例。
- **在线指标**：记录延迟、错误率、token、估算成本和人工修改率。

### 测试样例

```python
def test_prompt_keeps_resume_in_user_content():
    prompt = build_prompt("我是 Python 开发者", "需要 FastAPI")
    assert "我是 Python 开发者" in prompt
    assert "只根据提供内容" not in prompt  # 该规则应位于 SYSTEM_PROMPT

def test_score_boundary_is_valid():
    raw = '{"candidate_summary":"x","matched_skills":[],"missing_skills":[],' \
          '"match_score":0,"interview_questions":["q"]}'
    assert parse_analysis(raw).match_score == 0
```

评估结果必须保存失败样例，而不是只报告平均分。至少分类：JSON 格式失败、字段缺失、事实幻觉、检索/输入不足、超时和供应商错误。

### 练习

1. 为 `parse_analysis` 写成功、边界和失败参数化测试。
2. 扩展 `data/eval_cases.jsonl`，每行包含简历、职位描述和期望关键技能。
3. 编写脚本统计：解析成功率、技能命中率、平均延迟和每次请求成本。
4. 比较 temperature 为 0 和 0.7 的结果差异，记录结论。

## 第 5 课：FastAPI 服务化

### 请求与响应模型

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

class ResumeRequest(BaseModel):
    resume: str = Field(min_length=20, max_length=20_000)
    job_description: str = Field(min_length=20, max_length=20_000)

app = FastAPI(title="Resume Analysis API")

@app.post("/resume/analyze", response_model=ResumeAnalysis)
async def analyze(request: ResumeRequest):
    try:
        raw = await call_model(build_prompt(request.resume, request.job_description))
        return parse_analysis(raw)
    except TimeoutError as exc:
        raise HTTPException(504, "模型服务超时") from exc
    except ValueError as exc:
        raise HTTPException(502, "模型返回无法解析") from exc
```

不要把供应商异常原文返回给客户端。统一错误响应，日志中保留内部诊断信息。长文本建议使用后台任务或流式响应；本阶段先完成一次请求一次响应，再考虑 SSE。

### 练习

1. 为接口增加空文本、超长文本和模型失败测试。
2. 使用 FastAPI `TestClient`，把 `call_model` monkeypatch 成固定 mock。
3. 增加请求 ID 和耗时日志。
4. 用 `uvicorn` 启动服务并通过 `/docs` 手动验证。

## 阶段项目：简历分析助手

### 阶段项目运行顺序

先从不联网的 Mock 开始：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.mock_resume_analysis
```

然后直接运行真实 DeepSeek 示例。程序会读取电脑环境变量 `DEEPSEEK_API_KEY`：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.deepseek_resume_analysis
```

最后启动 API 并在 `/docs` 中调用，或运行 5 条评估样例：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.app.run_api
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.evaluate_deepseek
```

评估输出包含总样例数、结构化成功数、失败数、技能命中率和平均匹配分。评估只用于学习和比较，5 条样例不足以代表生产质量。

### 代码目录

```text
stages/phase2_resume_analysis/
├── README.md           # 阶段说明和运行命令
├── lesson.md           # 本阶段完整讲义
├── requirements.txt    # 本阶段依赖
├── .env.example        # DeepSeek 配置示例，不包含真实密钥
├── app/
│   ├── contracts.py    # Pydantic 请求/响应契约
│   ├── prompts.py      # Prompt 版本和构造
│   ├── client.py       # Fake/OpenAI 客户端与有限重试
│   ├── service.py      # 业务编排和解析诊断
│   ├── evaluation.py   # JSONL 评估和技能命中率
│   ├── api.py          # FastAPI app factory
│   └── run_api.py      # 本地真实 API 启动入口
├── examples/           # Mock、真实 DeepSeek 和批量评估入口
├── exercises/          # 课程练习及对应测试
├── tests/              # 阶段项目离线测试
├── data/               # JSONL 评估样例
└── docs/               # 阶段设计文档和实现计划
```

运行离线测试：`.\agent_env\Scripts\python.exe -m pytest stages\phase2_resume_analysis -q`。启动真实 API：`.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.app.run_api`。两条命令都应在仓库根目录执行。

### 最小功能

- 接收简历和职位描述；
- 返回摘要、匹配技能、缺失技能、0-1 匹配分和面试问题；
- 使用 Pydantic 严格校验；
- 网络超时、有限重试和统一错误响应；
- mock 单元测试与至少 10 条离线评估样例；
- README 写清启动命令、环境变量、架构和已知限制。

### 完成定义

1. 无 API Key 时测试仍可运行。
2. 真实 API Key 通过环境变量注入，仓库中没有密钥。
3. 非法 JSON、缺字段、越界分数和超时均有可观察、可解释的失败行为。
4. 能向面试官说明为什么“模型输出必须经过代码校验”，以及如何衡量系统质量。

### 推荐学习顺序

先完成第 1 课的 mock 和测试，再完成第 2 课的客户端适配器；然后实现第 3 课的诊断与恢复，接着建立第 4 课评估集，最后在第 5 课包装成 FastAPI。每完成一课，保留一次运行结果和一段复盘。
