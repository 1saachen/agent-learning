# 第二阶段核心知识手册：LLM、Prompt 与结构化输出

## 1. 学习目标与使用方法

这份手册解释简历分析项目背后的核心知识。目标不是记住术语，而是能够回答：它解决什么问题、它在项目哪一层出现、配置错误会怎样失败、应该怎样验证。

建议按“大模型基础 -> Prompt -> 结构化输出 -> 项目映射 -> 实验与验收”阅读。每学完一节，先合上文档，用自己的话复述，再完成对应实验。

当前项目结构：

```text
stages/phase2_resume_analysis/
├── app/
│   ├── contracts.py    # Pydantic 输入和输出契约
│   ├── prompts.py      # System Prompt、Few-shot、用户输入包装
│   ├── client.py       # DeepSeek 调用、timeout、网络重试
│   ├── service.py      # 调用编排、JSON 解析、Pydantic 校验
│   ├── api.py          # FastAPI 接口与错误映射
│   └── evaluation.py   # 离线评估
├── examples/           # Mock、真实调用和评估入口
├── tests/              # 离线测试
└── data/eval_cases.jsonl
```

---

# 第一部分：大模型基础

## 2. Token

### 2.1 Token 是什么

Token 是模型读取和生成文本时使用的基本计量单位，不严格等于汉字、字符或英文单词。文本会先经过 tokenizer，拆成模型词表中的 token。不同模型的 tokenizer 不同，同一段文字在不同模型中的 token 数也可能不同。

一次调用的 token 通常分为：

```text
input tokens  = System Prompt + 消息历史 + 用户输入 + 工具结果
output tokens = 模型生成内容
```

### 2.2 为什么重要

Token 同时影响：

- 是否超过上下文窗口；
- 调用成本；
- 响应延迟；
- 能带多少历史、文档和工具结果；
- 能为模型输出预留多少空间。

当前 [prompts.py](../app/prompts.py) 中的 System Prompt 和 Few-shot 每次都会发送，因此也占输入 token。Few-shot 能提高格式稳定性，但不是免费的。

### 2.3 常见误区

- 一个汉字不一定等于一个 token；
- 不只是用户输入计费，System Prompt、历史和输出也参与；
- Prompt 不是越长越好，冗余规则会增加成本并稀释重点；
- 字符数限制只是粗略保护，不等于精确 token 预算。

### 2.4 面试表达

> Token 是大模型处理文本的基本单位，影响上下文容量、成本和延迟。一次请求的输入 token 包括 System Prompt、历史、用户内容和工具结果。工程上我会限制输入、为输出预留预算、记录 usage，并控制重复上下文。

### 2.5 实验

用短、中、长三份虚构简历调用同一模型，记录输入 token、输出 token、耗时和估算费用，观察输入增长如何影响调用。

## 3. 上下文窗口

上下文窗口是模型一次请求能够处理的 token 总量上限，通常要同时容纳输入和输出：

```text
输入 token + 输出 token <= 上下文窗口
```

具体上限取决于模型版本，应以供应商文档为准。超过上限时，API 可能拒绝请求或截断内容。静默截断最危险，因为系统可能仍给出看似正常、实际缺少关键证据的答案。

Agent 比普通问答更容易占满上下文，因为还要携带：

- 多轮消息历史；
- 工具定义和工具调用结果；
- RAG 检索片段；
- 中间状态或计划；
- 最终输出空间。

常用策略：

- 在入口限制输入长度；
- 为输出预留 token；
- 只保留相关历史；
- 对旧对话做结构化摘要；
- 工具结果先过滤或裁剪；
- RAG 只放高相关片段；
- 超长文档采用分块和分层总结。

[contracts.py](../app/contracts.py) 使用字符串 `max_length` 做基础保护，但字符数不等于 token 数。更严格的系统还会使用 tokenizer 或实际 usage 数据进行预算。

面试时可以回答：

> 上下文窗口是单次请求可处理的 token 总量。大窗口只代表容量更大，不保证所有信息都能被同等准确地利用。Agent 应控制历史、工具结果和检索片段，并给输出预留空间。

## 4. Temperature

模型生成下一个 token 时，会给候选 token 分配概率。Temperature 调整概率分布：

- 较低：更偏向高概率候选，结果通常更稳定；
- 较高：候选更分散，结果通常更多样；
- `0`：通常最稳定，但不保证绝对可重复。

模型升级、服务端实现、浮点计算和并发都可能造成差异，所以不能把 `temperature=0` 当成传统确定性函数。

典型选择：

| 任务 | Temperature 倾向 |
| --- | --- |
| 信息抽取、分类、结构化 JSON | 低 |
| 事实问答、代码修改 | 较低 |
| 创意文案、头脑风暴 | 中高 |
| 需要多个候选方案 | 提高或多次采样 |

当前简历分析属于抽取与判断，因此 [client.py](../app/client.py) 使用 `temperature=0`。

常见误区：低 Temperature 不能消除幻觉；高 Temperature 不代表更聪明；它不负责控制答案长度，也不能保证 JSON 合法。

实验：对同一输入分别使用 `0` 和 `0.8` 各调用 5 次，比较字段完整率、技能列表、匹配分波动和面试问题多样性。

## 5. 长上下文问题

“能放进上下文”不代表模型“能用好上下文”。常见问题包括：

- **Lost in the middle**：更关注开头和结尾，忽略中间信息；
- **注意力稀释**：无关内容太多，关键证据占比下降；
- **指令冲突**：多份内容包含互相矛盾的要求；
- **错误累积**：旧对话中的错误持续进入后续请求；
- **成本和延迟上升**：每轮重复发送大量内容；
- **攻击面扩大**：更多外部内容意味着更多 Prompt Injection 风险。

处理原则：先过滤再放入；规则与不可信数据分隔；给文档附来源和位置；复杂任务拆成明确步骤；使用结构化状态而非无限历史；关键结论返回证据。

当前 [prompts.py](../app/prompts.py) 用 `<resume>` 和 `<job_description>` 分隔数据，并明确其中内容不是指令，这是基础边界，但不是完整安全机制。

## 6. 幻觉

幻觉是模型生成了流畅、合理，但没有输入或可靠来源支持的内容。例如简历只写 Python，模型却声称候选人有 Kubernetes 生产经验。

常见类型：

- 编造经历、技能、数字或引用；
- 从“学过”过度推断为“有多年生产经验”；
- 工具没有返回结果，却声称查询成功；
- JSON 格式完全正确，但字段内容没有事实依据。

最后一种尤其重要：Pydantic 能验证数据形状，不能验证事实真假。

降低幻觉的方法：

- 明确只根据给定来源回答；
- 允许模型表示“不确定”或请求补充信息；
- 为关键结论返回原文证据或来源 ID；
- 用 RAG 或工具取得可核查数据；
- 使用业务规则和评估集；
- 高风险动作加入人工确认。

不要依赖“请展示完整思维过程”校验事实。更实用的是要求简短、可核查的证据：

```json
{
  "skill": "FastAPI",
  "evidence": "使用 FastAPI 开发订单服务"
}
```

面试表达：

> Prompt、低 Temperature 和结构化输出只能降低部分风险，不能消除幻觉。我会限定来源、允许不确定、返回可核查证据，并使用代码规则、评估集和人工审核验证关键结果。

## 7. 流式输出

非流式调用等待完整结果后一次性返回；流式调用随着模型生成，逐块返回增量内容：

```text
非流式：请求 -> 等待 -> 完整响应
流式：  请求 -> chunk 1 -> chunk 2 -> chunk 3 -> 完成
```

流式输出能降低首字延迟、改善长回答体验，但不会减少模型的总计算时间。

难点包括：

- 中途断线和取消；
- 如何传递错误事件；
- 如何获得最终 usage；
- 代理可能缓冲响应；
- 半个 JSON 不能通过解析和 Pydantic 校验；
- 已经显示的错误内容难以收回。

例如下面的增量内容还不是合法 JSON：

```text
{"candidate_summary": "候选人具
```

所以结构化输出一般要在流结束后整体校验。当前项目优先保证结果可靠，使用非流式调用。以后可以流式发送“正在分析”等状态事件，最终业务 JSON 仍一次性返回。

## 8. 模型成本

模型直接费用通常近似为：

```text
费用 = 输入 token × 输入单价 + 输出 token × 输出单价
```

系统总成本还包括重试、输出修复、Embedding、Rerank、数据库、服务器、监控和人工审核。

常用优化方法：

- 选择满足任务质量的最小模型；
- 精简重复 Prompt 和历史；
- 限制输入与最大输出；
- 对确定性重复请求使用缓存；
- 只重试临时错误；
- 简单规则先用代码处理；
- 记录 usage 后再优化。

删除 Few-shot 虽然减少单次输入 token，却可能增加格式错误和修复请求。应比较“每个成功业务结果的成本”，而不是只看单次价格。

推荐记录：`request_id`、模型、输入/输出 token、延迟、重试次数、解析是否成功和估算成本。不要记录 API Key；完整简历也不应默认进入普通日志。

## 9. 模型调用超时与重试

网络调用必须设置 timeout，否则供应商拥塞、代理或连接问题可能长期占用服务资源。当前 [client.py](../app/client.py) 设置了 30 秒 timeout。

适合有限重试：

- timeout；
- 临时连接失败；
- `429` 限流；
- `500`、`502`、`503`、`504` 等上游临时错误。

通常不适合原样重试：

- `400` 参数错误；
- `401` API Key 错误；
- `403` 权限不足；
- `404` 地址或模型名错误；
- Pydantic 业务校验失败。

重试必须有最大次数和退避，生产环境还应尊重 `Retry-After` 并控制总时间预算。对于发邮件、扣款、创建任务等有副作用的工具，重试前还必须考虑幂等性。

特别要区分：

```text
网络重试：没有成功获得响应，稍后重复同一请求。
输出修复：已获得响应，但 JSON 或字段无效，带错误反馈重新生成。
```

当前项目实现了网络重试；无效输出会返回 `ParseFailure`，尚未实现自动修复循环。

---

# 第二部分：Prompt

## 10. System、User、Assistant 消息

**System 消息**定义高层任务、稳定规则、安全边界、输出契约和不确定策略。

**User 消息**承载本次请求和输入数据，例如简历与职位描述。

**Assistant 消息**表示模型之前的回答；多轮对话和使用消息形式的 Few-shot 会用到它。

当前映射：

- [prompts.py](../app/prompts.py) 的 `SYSTEM_PROMPT` 定义长期规则；
- `build_analysis_prompt()` 包装本次简历与职位描述；
- [client.py](../app/client.py) 组合消息数组并发送给 DeepSeek。

常见错误：把用户输入拼进 System Prompt；无限重复完整历史；把 Assistant 历史当成可信事实；把密钥放进 System Prompt。

System Prompt 不是安全存储位置。消息角色能提供指令层次，但不是传统权限系统，不能单独防止 Prompt Injection。

## 11. 角色设定

角色设定提供任务视角和行为倾向。例如：

```text
你是一个客观、谨慎的技术招聘助手。
```

有效角色应与任务相关、描述可观察行为、明确范围并与其他规则一致。“你是世界上最聪明的专家”没有给出可执行要求。

角色不能替代具体契约。只写“你是招聘专家”无法保证字段完整、拒绝幻觉或输出合法 JSON。

面试表达：

> 角色设定用于提供任务视角和行为倾向，但属于弱约束。可靠 Prompt 还需要明确任务、输入边界、输出契约、异常策略和示例，结果仍要经过代码验证。

## 12. Few-shot

Few-shot 是在 Prompt 中提供少量输入输出示例，让模型学习任务模式。没有示例叫 zero-shot，一个示例也常称 one-shot。

当前 [prompts.py](../app/prompts.py) 的示例展示：输入如何分隔、必须返回哪些字段、匹配与缺失技能如何区分、怎样生成面试问题。

选择示例时应注意：

- 示例必须正确并符合当前 Schema；
- 覆盖代表性边界，而不只是理想案例；
- 不使用真实敏感信息；
- Schema 修改后同步更新示例；
- 用评估判断示例数量，不是越多越好。

Few-shot 会增加 token 和成本，也可能造成机械复制与示例偏差。合理方法是比较 zero-shot 与 few-shot 的结构化成功率和业务质量。

实验：临时移除 Few-shot，用同一组样例运行，记录字段完整率；恢复后再次运行，比较收益和 token 增量。

## 13. 约束输出

业务程序不能稳定消费任意自然语言。输出约束通常采用四层防线：

1. Prompt 描述字段和规则；
2. Few-shot 展示正确格式；
3. API 的 JSON 模式或严格 JSON Schema 约束生成；
4. 本地 Pydantic 最终验证。

一个完整契约应说明：字段名、类型、必填性、数值范围、数组长度、枚举值、缺少信息时如何处理、是否允许额外字段、是否允许解释文字。

`response_format={"type": "json_object"}` 通常只能提高合法 JSON 的概率，不能保证字段完整。之前 DeepSeek 返回 `assessment`，但缺少 `candidate_summary` 和 `interview_questions`，正说明：

```text
合法 JSON != 合法业务对象
```

严格 Schema 的支持依赖供应商，本地校验始终需要保留。

## 14. 任务拆分

一个请求同时做抽取、判断、搜索、计算和报告生成，容易导致 Prompt 难维护、错误难定位、任一步失败就全部重做。

简历分析可以拆成：

```text
提取职位技能
  -> 提取简历技能与证据
  -> 比较差异
  -> 生成面试问题
  -> 汇总结构化结果
```

拆分能提高可测试性、可观察性和局部重试能力，但会增加调用次数、延迟和成本。如果一次调用已经稳定满足评估，不必为了“像 Agent”强行拆分。

适合拆分的信号：某一步错误率高、需要独立证据、输入很长、步骤需要不同模型或确定性工具。

## 15. 让模型说明判断依据

需要的是可核查证据，而不是冗长的思维过程。例如：

```json
{
  "skill": "FastAPI",
  "evidence": "使用 FastAPI 开发订单服务"
}
```

证据可以与输入原文比较。推荐要求简短结论、原文片段或来源 ID，并限制证据长度；无证据时必须表示不确定。

当前项目可以升级为：

```python
class SkillEvidence(BaseModel):
    skill: str
    evidence: str
```

然后将匹配技能定义成 `list[SkillEvidence]`。这会影响 Model、Prompt、Few-shot、评估和测试，应该作为一项完整功能修改。

## 16. 让模型拒绝不确定回答

强迫模型对任何输入都给出确定答案，会增加编造风险。可靠系统要提供合法的不确定表达：`null`、`unknown`、空数组、“信息不足”或请求用户补充。

当前项目用 `years_of_experience=0` 表示没有明确年限，但这会混淆“明确零年”和“未知”。更精确的定义是：

```python
years_of_experience: int | None = Field(default=None, ge=0)
```

只在 Prompt 中说“不要编造”还不够。Schema 必须允许不确定，Few-shot 要展示不确定案例，API/UI 要正确展示，评估集也要包含信息不足样例。

---

# 第三部分：结构化输出

## 17. JSON Schema

JSON 是数据：

```json
{"match_score": 0.8}
```

JSON Schema 是描述数据应满足什么结构的规则：

```json
{
  "type": "object",
  "properties": {
    "match_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 1
    }
  },
  "required": ["match_score"]
}
```

Schema 可以描述类型、必填字段、枚举、范围、长度、嵌套结构和额外字段策略。

Pydantic 可以生成 JSON Schema：

```python
from stages.phase2_resume_analysis.app.contracts import ResumeAnalysis

print(ResumeAnalysis.model_json_schema())
```

Schema 能保证 `match_score` 是 `0–1` 的数字，却不能保证分数判断合理；能保证技能是字符串数组，却不能保证技能真的出现在简历中。语义质量仍需要业务验证和评估。

## 18. Pydantic Model

Pydantic 使用 Python 类型注解定义数据模型，并在运行时解析和校验。当前核心模型：

```text
ResumeRequest   = API 输入契约
ResumeAnalysis  = 模型输出契约
```

常用方法：

```python
ResumeAnalysis.model_validate(data)  # dict -> 模型
result.model_dump()                   # 模型 -> dict
result.model_dump_json(indent=2)      # 模型 -> JSON 字符串
ResumeAnalysis.model_json_schema()    # 模型 -> JSON Schema
```

Pydantic 默认可能执行类型转换。例如字符串数字有时会变成整数。需要严格类型时可以使用严格字段或 `ConfigDict(strict=True)`。

如果不允许模型返回额外字段，可以设置：

```python
from pydantic import ConfigDict

class ResumeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

这样 `assessment` 等未定义字段会触发验证失败。是否采用应由业务契约决定，并配测试。

## 19. 枚举字段

字段只能从有限集合选择时，应使用 `Literal` 或 `Enum`，而不是任意字符串。

```python
from typing import Literal

match_level: Literal[
    "strong_match",
    "potential_match",
    "weak_match",
]
```

或者：

```python
from enum import Enum

class MatchLevel(str, Enum):
    STRONG = "strong_match"
    POTENTIAL = "potential_match"
    WEAK = "weak_match"
```

值少且只在一处使用时 `Literal` 更轻；需要复用或领域方法时 `Enum` 更清晰。

增加枚举字段必须同步三处：Pydantic Model、Prompt/Few-shot、测试/评估。只改 Prompt 没有硬校验；只改模型则模型不知道允许值。

## 20. 字段校验

当前项目使用：

```python
match_score: float = Field(ge=0, le=1)
interview_questions: list[str] = Field(min_length=1, max_length=10)
years_of_experience: int = Field(default=0, ge=0)
```

常见单字段约束包括长度、范围、正则、默认值和是否允许 `None`。

自定义字段校验器可用于技能去重：

```python
from pydantic import field_validator

@field_validator("matched_skills")
@classmethod
def unique_skills(cls, value: list[str]) -> list[str]:
    return list(dict.fromkeys(skill.strip() for skill in value if skill.strip()))
```

跨字段规则需要 `model_validator`。例如同一技能不能同时匹配和缺失：

```python
from pydantic import model_validator

@model_validator(mode="after")
def skills_must_not_overlap(self):
    overlap = set(self.matched_skills) & set(self.missing_skills)
    if overlap:
        raise ValueError(f"技能不能同时匹配和缺失: {overlap}")
    return self
```

Pydantic 适合确定、快速、无外部副作用的数据规则。数据库访问、模型调用等复杂验证应放在 service 层。

## 21. 无效 JSON 的修复

常见问题：Markdown 代码围栏、JSON 前后解释、单引号、尾随逗号、字符串未闭合、输出截断、字段类型错误，以及 JSON 合法但不符合 Pydantic。

推荐处理顺序：

1. **生成前预防**：明确格式、Schema、Few-shot、供应商结构化输出；
2. **严格解析**：`json.loads()` 后执行 `model_validate()`；
3. **有限确定性清理**：只处理明确包装，例如完整 `json` 代码围栏；
4. **模型修复**：带 Schema 和简短校验错误重新生成一次；
5. **仍失败则结束**：返回 `ParseFailure`，不能无限循环。

安全流程：

```text
原始响应
  -> json.loads
语法失败？ -> 明确清理一次 -> 再解析
  -> Pydantic 校验
校验失败？ -> 构造修复 Prompt -> 调用一次 -> 再校验
仍失败 -> ParseFailure
```

不要用 `eval()` 解析模型输出，也不要用贪婪正则从任意文字中猜 JSON。修复会再次消耗 token，也可能再次发送敏感内容，因此必须限制次数并控制日志。

## 22. 重试机制

“重试”至少有三类：

| 类型 | 触发原因 | 下一次请求 | 常见限制 |
| --- | --- | --- | --- |
| 网络重试 | timeout、429、5xx | 基本相同 | 2–3 次与退避 |
| 输出修复 | JSON/Pydantic 失败 | 加入错误反馈 | 1–2 次 |
| Agent 重新规划 | 工具结果不足、计划失败 | 改变下一步行动 | 最大步骤与成本预算 |

网络重试属于 [client.py](../app/client.py)，它不理解 `ResumeAnalysis`。输出修复应该位于 service 或 parser/repair 层，因为这一层理解 Schema。进入 Tool Calling 后，重新选工具属于 Agent 控制循环，必须限制最大步骤、重复调用和成本。

面试表达：

> 我会区分网络重试、输出修复和 Agent 重新规划。网络临时错误可以退避重试；结构化输出失败要带校验反馈修复，不能原样重复；Agent 循环则需要最大步骤和预算。三者都必须有终止条件和可观察日志。

---

# 第四部分：项目映射与验收

## 23. 一次请求的完整数据流

```text
用户提交简历和职位描述
        ↓
ResumeRequest：检查类型和长度
        ↓
build_analysis_prompt：分隔两段不可信数据
        ↓
OpenAIModelCaller：读取 DEEPSEEK_API_KEY，组合 System/User 消息
        ↓
call_with_retry：处理 timeout、connection、429 和 5xx
        ↓
DeepSeek 返回 raw: str
        ↓
json.loads：检查 JSON 语法
        ↓
ResumeAnalysis.model_validate：检查字段、类型和范围
        ↓
成功：ResumeAnalysis；失败：ParseFailure
        ↓
FastAPI：200 / 422 / 502 / 504
```

## 24. 知识点与代码索引

| 知识点 | 阅读文件 |
| --- | --- |
| 消息角色、Temperature、DeepSeek 调用 | `app/client.py` |
| timeout、网络重试 | `app/client.py`、`tests/test_phase2_client.py` |
| 角色、Few-shot、约束输出 | `app/prompts.py` |
| Pydantic、字段约束、JSON Schema | `app/contracts.py` |
| JSON 解析、ParseFailure | `app/service.py` |
| HTTP 错误映射 | `app/api.py` |
| 评估与技能命中率 | `app/evaluation.py` |
| 无网络测试 | `examples/mock_resume_analysis.py`、`tests/` |
| 真实 DeepSeek 调用 | `examples/deepseek_resume_analysis.py` |

## 25. 当前项目的已知限制

- 没有记录 token usage、延迟和估算成本；
- 没有流式输出；
- 没有自动 JSON 修复；
- `years_of_experience=0` 混淆“零年”和“未知”；
- 技能没有附带原文证据；
- 评估集较小，指标不够全面；
- API 对上游错误的映射比较简化；
- 没有持久化、认证、限流和生产监控；
- 它是可靠的 LLM 工作流，但还不是能自主选择工具的 Agent。

主动说明限制并给出下一步，比声称“已经生产可用”更有说服力。

## 26. 十个动手实验

1. **Token**：比较短、中、长输入的 usage、延迟和费用。
2. **Temperature**：用 `0` 和 `0.8` 各运行 5 次，比较稳定性。
3. **长上下文**：把关键技能放在开头、中间和结尾，加入无关内容。
4. **幻觉**：简历只写 Python，职位要求 Kubernetes，检查模型是否误判匹配。
5. **Few-shot 消融**：临时移除 Few-shot，比较结构化成功率，再恢复。
6. **枚举字段**：增加 `match_level`，同步 Model、Prompt、Mock 和测试。
7. **跨字段校验**：禁止同一技能同时出现在匹配和缺失列表。
8. **不确定状态**：把工作年限改为 `int | None`，让未知返回 `null`。
9. **一次输出修复**：第一次返回坏 JSON，第二次修复；最多调用一次修复。
10. **证据字段**：为匹配技能增加原文证据，并检查证据是否出现在简历。

所有功能修改都应先写失败测试，再修改实现。

## 27. 掌握度检查表

### 大模型基础

- [ ] 能解释 token 为什么不等于字符或单词；
- [ ] 能说明上下文窗口由哪些内容占用；
- [ ] 能解释 Temperature 的作用和边界；
- [ ] 能列出至少三种长上下文问题；
- [ ] 能解释为什么 Pydantic 不能阻止事实幻觉；
- [ ] 能说明流式结构化输出的困难；
- [ ] 能写出成本的基本计算思路；
- [ ] 能区分可重试和不可重试错误。

### Prompt

- [ ] 能说明 System、User、Assistant 的职责；
- [ ] 能写具体、与任务相关的角色设定；
- [ ] 能设计正确的 Few-shot；
- [ ] 能列出输出契约必须说明的内容；
- [ ] 能判断任务是否值得拆分；
- [ ] 能区分可核查证据与冗长推理；
- [ ] 能在 Schema 中表达“不确定”。

### 结构化输出

- [ ] 能区分 JSON、JSON Schema 和 Pydantic Model；
- [ ] 能使用 `Literal` 或 `Enum`；
- [ ] 能写字段校验和跨字段校验；
- [ ] 能解释合法 JSON 为什么仍可能失败；
- [ ] 能设计有次数限制的输出修复；
- [ ] 能区分网络重试、输出修复和 Agent 重新规划。

## 28. 面试高频问答

**Prompt 已经规定 JSON，为什么还需要 Pydantic？**

Prompt 是概率性的软约束，Pydantic 是代码执行的硬约束。模型仍可能漏字段、改字段名或输出越界值，必须在信任数据前本地验证。

**Temperature 为 0 是否保证完全相同？**

不保证。它通常提高稳定性，但模型升级、服务端实现和数值计算仍可能造成差异。

**大上下文模型是否不需要 RAG？**

不是。大窗口只提高容量，不保证相关性、准确利用、成本、来源和权限隔离。RAG 仍能筛选相关内容并提供可核查来源。

**为什么不能所有错误都重试？**

认证、权限和参数错误重复相同请求不会恢复，只增加延迟。只有可能暂时恢复的 timeout、connection、429 和 5xx 适合有限退避重试。

**JSON 模式能保证业务字段吗？**

通常只能保证输出是 JSON，不能保证必填字段、字段名和业务范围。严格 Schema 支持也依赖供应商，本地验证必须保留。

**如何减少幻觉？**

限定来源，允许不确定或拒答，为关键结论返回证据，用工具或 RAG 获取事实，再通过业务规则、评估集和人工审核验证。

## 29. 阶段二完成标准

当你能不看代码画出第 23 节的数据流，并独立完成实验 6、7 或 9 中任意两个，就可以进入阶段三 Tool Calling。

进入下一阶段前，应能清楚表达：

> 当前项目是可靠的 LLM 工作流：Prompt 提高模型按契约输出的概率，Pydantic 守住数据边界，客户端处理上游 timeout 和重试，评估集验证业务质量。下一阶段将在此基础上加入工具定义、模型选择工具、代码执行工具、结果回传和最大步骤限制。
