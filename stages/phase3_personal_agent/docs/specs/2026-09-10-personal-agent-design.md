# 第三阶段个人研究助手设计

> 日期：2026-09-10  
> 状态：已确认，等待实现计划

## 1. 目标

实现一个基于 DeepSeek Tool Calling 的单 Agent 项目，让学习者能够完整理解并运行以下循环：

```text
用户请求
  -> 模型判断是否调用工具
  -> 本地校验工具名和参数
  -> Python 执行工具
  -> 工具结果回传模型
  -> 模型继续调用工具或生成最终回答
  -> 达到最大步骤数时停止
```

项目首先服务于 Agent 开发学习，同时具备可作为初级实习作品集项目继续扩展的工程结构。默认运行入口直接调用真实 DeepSeek API，工具也执行真实读取、写入和天气查询。

## 2. 范围

第一版包含三个工具：

1. `search_notes`：搜索阶段目录下的本地 Markdown 笔记；
2. `create_todo`：将待办写入阶段目录下的 JSON 文件；
3. `get_weather`：通过 Open-Meteo 查询城市的实时天气。

第一版还必须包含：

- DeepSeek OpenAI 兼容客户端；
- 工具定义和 JSON Schema；
- Pydantic 工具参数校验；
- 工具注册表和统一执行入口；
- 最多 5 步的 Agent 控制循环；
- 重复工具调用保护；
- 工具异常转换为可回传的结构化结果；
- 不包含 API Key 的结构化运行轨迹；
- 真实命令行运行入口；
- 不产生模型费用的自动化测试；
- 与代码对应的第三阶段讲义。

## 3. 非目标

第一版不实现：

- LangChain、LangGraph 或其他 Agent 框架；
- Web 搜索、浏览器自动化或网页抓取；
- 多 Agent 协作；
- 长期对话记忆、向量数据库或 RAG；
- FastAPI 和前端界面；
- 用户系统、远程数据库和云部署；
- 对任意路径的文件读取或写入；
- 自动执行 shell、Python 代码或其他高风险操作。

这些能力会掩盖 Tool Calling 的核心机制，或属于后续阶段。

## 4. 目录结构

```text
stages/phase3_personal_agent/
├── README.md
├── lesson.md
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── client.py
│   ├── contracts.py
│   ├── prompts.py
│   ├── registry.py
│   └── tools/
│       ├── __init__.py
│       ├── notes.py
│       ├── todo.py
│       └── weather.py
├── data/
│   ├── notes/
│   │   └── agent-basics.md
│   └── todos.json
├── docs/
│   ├── phase3-core-knowledge-guide.md
│   ├── plans/
│   └── specs/
├── examples/
│   ├── __init__.py
│   └── run_agent.py
└── tests/
    ├── __init__.py
    ├── test_agent.py
    ├── test_client.py
    ├── test_registry.py
    └── test_tools.py
```

阶段三与阶段二保持相同的组织方式：应用代码、运行示例、测试、数据和学习资料全部位于自己的阶段目录中。

## 5. 组件设计

### 5.1 数据契约

`contracts.py` 定义边界数据模型，至少包括：

- 三个工具各自的参数模型；
- 统一的工具执行成功和失败结果；
- 单步运行轨迹；
- Agent 最终运行结果；
- 最大步骤、重复调用等终止原因。

所有来自模型的工具参数必须先经过 `json.loads()` 和对应 Pydantic Model 校验。业务代码不能直接使用模型返回的原始字典。

### 5.2 DeepSeek 客户端

`client.py` 使用 OpenAI 兼容的异步客户端：

```python
response = await client.chat.completions.create(
    model=model,
    messages=messages,
    tools=tools,
    tool_choice="auto",
    temperature=0,
)
```

配置约定：

- API Key：读取电脑环境变量 `DEEPSEEK_API_KEY`；
- Base URL：默认 `https://api.deepseek.com`；
- Model：默认 `deepseek-v4-pro`；
- 可通过 `LLM_BASE_URL` 和 `LLM_MODEL` 覆盖；
- 不要求在运行前重复通过终端配置环境变量；
- 模型请求必须有 timeout，并只对临时网络错误进行有限重试。

客户端只负责模型通信和供应商错误转换，不执行工具，也不决定 Agent 的终止条件。

### 5.3 工具注册表

`registry.py` 是工具定义和 Python 实现之间的唯一映射层。每个注册项包含：

- 唯一工具名；
- 给模型看的用途描述；
- Pydantic 参数模型；
- 实际执行函数；
- 由参数模型生成的 JSON Schema。

注册表提供：

```text
list_definitions()  -> 发送给模型的 tools 数组
execute(name, args) -> 校验并执行工具
```

如果模型请求不存在的工具、参数不是合法 JSON 或参数不满足 Schema，注册表返回失败结果，不执行任何函数。

### 5.4 Agent 控制循环

`agent.py` 负责维护消息历史和运行状态：

1. 写入 System 和 User 消息；
2. 把工具定义发送给 DeepSeek；
3. 如果模型返回普通文本，将其作为最终回答；
4. 如果返回一个或多个 `tool_calls`，先把完整 Assistant 消息加入历史；
5. 依次校验并执行工具；
6. 每个结果作为包含对应 `tool_call_id` 的 Tool 消息加入历史；
7. 再次调用模型；
8. 达到最大 5 步时停止并返回明确的终止原因。

一步指一次模型决策。模型在一步中返回多个工具调用时，这些调用属于同一步，但分别记录轨迹。

重复调用使用标准化后的 `(tool_name, canonical_arguments)` 作为签名。同一签名在一次运行中再次出现时不重复执行，而是向模型返回 `duplicate_tool_call` 错误。这样可以阻止天气查询或待办写入陷入循环，并避免重复副作用。

### 5.5 Prompt

System Prompt 要求模型：

- 需要外部事实或操作时使用工具，不编造工具结果；
- 只调用已提供的工具；
- 工具参数必须符合 Schema；
- 工具失败后根据错误调整一次，不能反复提交相同调用；
- 创建待办前必须从用户请求中获得明确意图；
- 最终回答简洁说明已查询的信息和已执行的操作；
- 不声称未实际完成的操作已经成功。

工具能力、参数和约束主要由工具 Schema 表达，Prompt 不重复维护一份容易漂移的字段清单。

## 6. 工具设计

### 6.1 搜索本地笔记

输入：

```json
{
  "query": "Tool Calling",
  "max_results": 5
}
```

行为：

- 只搜索固定的 `data/notes/` 目录；
- 只读取 `.md` 文件；
- 使用不区分大小写的文本匹配；
- 返回命中文件的相对路径、行号和短文本片段；
- `max_results` 有较小上限，防止把大量文件内容塞回上下文；
- 不接受来自模型的文件路径。

### 6.2 创建待办

输入：

```json
{
  "title": "出门带外套",
  "due_date": null,
  "priority": "high"
}
```

约束：

- `title` 去除首尾空白后必须非空，并限制长度；
- `due_date` 为可选的 ISO 日期 `YYYY-MM-DD`；
- `priority` 只能是 `low`、`medium`、`high`；
- 待办 ID 由程序生成，模型不能指定；
- 数据只写入固定的 `data/todos.json`；
- JSON 文件初始结构为数组；
- 写入采用临时文件替换，避免中途失败破坏原文件；
- 返回创建后的 ID 和规范化字段。

创建待办有副作用，因此重复调用保护必须在写文件之前完成。

### 6.3 查询真实天气

输入：

```json
{
  "city": "上海"
}
```

查询过程：

1. 调用 Open-Meteo Geocoding API，将城市名解析为经纬度和标准地点名；
2. 调用 Open-Meteo Forecast API，请求 `current` 天气字段；
3. 返回地点、当地时间、温度、体感温度、降水、天气代码和风速；
4. 对天气代码做程序化描述，不让模型猜测代码含义。

Open-Meteo 无需额外 API Key。两个 HTTP 请求都必须设置 timeout；无匹配城市、限流、上游错误、响应格式变化和网络失败均转换成工具失败结果，由模型决定怎样向用户解释。

## 7. 错误处理

错误按边界处理：

| 错误 | 处理位置 | 结果 |
| --- | --- | --- |
| 缺少 DeepSeek API Key | 客户端初始化 | 启动失败并给出明确配置说明 |
| DeepSeek timeout、连接错误、429、5xx | 客户端 | 有限退避重试，耗尽后抛出模型调用错误 |
| DeepSeek 认证或参数错误 | 客户端 | 不重试，立即失败 |
| 未知工具 | 注册表 | 返回 `unknown_tool` 给模型 |
| 工具参数 JSON 无效 | 注册表 | 返回 `invalid_arguments` 给模型 |
| Pydantic 校验失败 | 注册表 | 返回精简字段错误给模型 |
| 工具内部或网络失败 | 工具边界 | 返回 `tool_execution_error` 给模型 |
| 重复工具调用 | Agent 循环 | 不执行，返回 `duplicate_tool_call` |
| 超过最大步骤 | Agent 循环 | 返回 `max_steps_exceeded` 和已有轨迹 |

错误回传不包含栈信息、API Key、绝对路径或完整敏感文件内容。

## 8. 运行轨迹

每次运行返回最终回答和结构化 trace。每条轨迹至少记录：

- 步骤号；
- 工具调用 ID；
- 工具名；
- 校验后的参数；
- 成功或失败；
- 结果摘要或错误类型；
- 工具耗时。

第一版在命令行中展示 trace，不做数据库持久化。日志不输出 `DEEPSEEK_API_KEY`，也不默认记录完整模型请求和完整笔记内容。

## 9. 测试策略

运行入口使用真实 DeepSeek 和真实工具，但自动化测试不能依赖模型网络和模型随机性。因此测试通过可注入的 Fake Model Client 提供确定响应，这属于测试替身，不是面向学习者的 Mock 运行模式。

测试至少覆盖：

- 模型直接返回最终回答；
- 调用一个工具后返回最终回答；
- 先查天气、再根据结果创建待办；
- 同一步返回多个工具调用；
- 未知工具；
- 非法 JSON 参数；
- Pydantic 参数校验失败；
- 工具执行异常；
- 重复工具调用被拦截；
- 达到最大步骤数；
- 笔记搜索不能越过固定目录；
- 待办成功写入且 ID 唯一；
- 待办写入失败不破坏原文件；
- 天气 geocoding 无结果和上游失败；
- 客户端消息及工具定义正确传给 DeepSeek。

天气工具测试使用受控 HTTP 响应，避免把第三方服务可用性当成单元测试条件。另提供手动真实运行步骤验证 DeepSeek 和 Open-Meteo 集成。

## 10. 学习顺序

讲义与代码按以下顺序组织：

1. 理解 Tool Calling 协议和消息角色；
2. 阅读三个工具参数模型及 JSON Schema；
3. 独立运行每个真实工具；
4. 阅读注册表如何完成查找、校验和执行；
5. 阅读 DeepSeek 返回的 `tool_calls`；
6. 单步跟踪 Agent 消息历史；
7. 理解多步循环和终止条件；
8. 注入失败，观察工具错误怎样回传模型；
9. 阅读测试，理解如何稳定测试概率性系统；
10. 完成扩展练习和面试复述。

## 11. 验收标准

项目完成时必须满足：

- 命令行入口可以真实调用 DeepSeek；
- 可以查询 Open-Meteo 实时天气；
- 可以搜索项目内 Markdown 笔记；
- 可以把待办真实写入 JSON；
- 能完成“查询天气，满足条件后创建待办”的多步任务；
- 所有模型工具参数均经过 Pydantic 校验；
- 未知、非法、失败和重复工具调用不会导致程序崩溃或重复副作用；
- Agent 最多运行 5 步并有明确终止原因；
- trace 能展示模型与工具之间的执行路径；
- 自动化测试不调用真实 DeepSeek，不产生模型费用；
- README 给出 Windows PowerShell 安装和运行命令；
- 讲义能解释 Tool Calling、工具 Schema、控制循环、安全边界和测试方法。

学习者应能不看代码画出模型、Agent 循环、工具注册表和三个工具之间的数据流，并解释为什么“模型提出工具调用”和“程序实际执行工具”必须分开。
