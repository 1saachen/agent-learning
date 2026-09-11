# 第三阶段讲义：Tool Calling 与单 Agent

## 1. 本阶段要解决的问题

第二阶段的程序只有一条固定路径：输入简历，调用模型，校验结构化结果。第三阶段允许模型根据当前状态选择下一步动作：直接回答、查询天气、搜索笔记或创建待办。

核心变化不是“多写几个函数”，而是增加了一个受控循环：

```text
用户 -> 模型决策 -> 工具执行 -> 工具结果 -> 模型再次决策 -> 最终回答
```

模型只负责提出工具调用。Python 程序保留工具查找、参数校验、权限判断和实际执行权。这条边界是理解 Agent 安全性的起点。

学完后你应该能：

- 解释 Tool Calling 协议；
- 从 Pydantic Model 生成工具 JSON Schema；
- 正确处理 Assistant 与 Tool 消息；
- 实现有终止条件的 Agent 循环；
- 防止非法参数、未知工具、重复调用和无限循环；
- 使用 Fake Model Client 稳定测试 Agent；
- 运行真实 DeepSeek 多步工具调用。

## 2. 先运行，再读代码

安装并运行：

```powershell
.\agent_env\Scripts\python.exe -m pip install -r stages\phase3_personal_agent\requirements.txt
.\agent_env\Scripts\python.exe -m stages.phase3_personal_agent.examples.run_agent
```

输入：

```text
查询上海当前天气。如果温度低于 20 摄氏度，创建一个标题为“出门带外套”的高优先级待办；否则只告诉我天气。
```

观察两种输出：最终自然语言回答和执行轨迹。不要一开始只看最终答案；Agent 工程真正需要调试的是轨迹。

## 3. 第一层：工具参数契约

打开 `app/contracts.py`。三个工具的输入分别由三个 Pydantic Model 定义：

```python
class SearchNotesArgs(BaseModel):
    query: str
    max_results: int

class CreateTodoArgs(BaseModel):
    title: str
    due_date: date | None
    priority: Literal["low", "medium", "high"]

class GetWeatherArgs(BaseModel):
    city: str
```

这些模型有两个消费者：

1. `model_json_schema()` 生成给模型看的参数 Schema；
2. `model_validate()` 校验模型真正返回的参数。

Schema 告诉模型“应该怎样输出”，Pydantic 决定程序“实际上接受什么”。模型即使看过 Schema，仍然可能返回未知优先级、空城市、错误日期或非 JSON 内容，所以两者都需要。

重点观察 `_TrimmedTextModel`：它在长度校验前去除首尾空白，因此三个空格不会被误认为长度为 3 的有效标题。

### 练习

不运行代码，判断下面哪些参数能通过校验：

```json
{"title": "复习", "priority": "urgent"}
{"title": "  复习  ", "due_date": null, "priority": "high"}
{"city": "   "}
{"query": "agent", "max_results": 11}
```

然后用 `model_validate()` 验证自己的答案。

## 4. 第二层：真实工具

### 4.1 笔记搜索

`app/tools/notes.py` 只遍历固定目录的 `*.md`：

```python
for path in sorted(notes_dir.glob("*.md")):
```

模型只能提供查询词和结果数量，不能提供文件路径。这比接收 `path` 后再尝试过滤更容易审计。返回值只包含文件名、行号和最多 300 字符的片段，避免整份文档进入上下文。

当前算法是大小写无关的子字符串匹配。它不是语义检索，因此“工具调用”不一定匹配英文 `Tool Calling`。第四阶段会用 Chunk、Embedding 和 RAG 解决语义检索问题。

### 4.2 待办写入

`app/tools/todo.py` 是有副作用的工具。它执行：

```text
读取原 JSON -> 验证必须是数组 -> 添加程序生成的记录
-> 写入同目录临时文件 -> 原子替换正式文件
```

为什么不用直接 `write_text()`？如果程序写到一半崩溃，原文件可能只剩半段 JSON。临时文件完整写完后再替换，可以显著缩小损坏窗口。

待办 ID 和 `created_at` 由程序生成，而不是交给模型。模型不应该控制资源标识、审计时间等可信字段。

### 4.3 实时天气

`app/tools/weather.py` 调用两个 Open-Meteo 接口：

```text
城市名 -> Geocoding API -> 经纬度
经纬度 -> Forecast API -> 当前天气
```

天气代码由 Python 的 `WMO_WEATHER` 映射解释，模型不需要猜数字含义。外部 HTTP 状态错误、无城市结果和响应字段缺失都会变成 `WeatherToolError`。

注意：HTTP 200 只表示请求成功，不保证 JSON 业务结构符合预期。外部 API 响应也必须校验。

## 5. 第三层：工具注册表

打开 `app/registry.py`。`ToolSpec` 把四件事绑定在一起：

```text
工具名 + 给模型的描述 + 参数模型 + Python handler
```

`ToolRegistry.definitions()` 生成 OpenAI 兼容工具定义：

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "查询指定城市当前的真实天气。",
    "parameters": {
      "type": "object",
      "properties": {
        "city": {"type": "string"}
      },
      "required": ["city"]
    }
  }
}
```

`execute()` 的顺序非常重要：

```text
查找工具名
 -> json.loads
 -> 确认参数是对象
 -> Pydantic 校验
 -> 执行 handler
 -> 统一包装 ToolExecutionResult
```

如果顺序反过来，非法参数可能在验证前触发网络请求或文件写入。

注册表把错误分成：

- `unknown_tool`：模型请求了不存在的工具；
- `invalid_arguments`：JSON 或字段不合法；
- `tool_execution_error`：参数合法，但真实执行失败。

模型看到错误类型后可以调整下一步，用户看不到内部栈信息。

## 6. 第四层：DeepSeek Tool Calling

`app/client.py` 发送：

```python
response = await client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=messages,
    tools=tool_definitions,
    tool_choice="auto",
    temperature=0,
    timeout=30,
)
```

`tool_choice="auto"` 表示模型可以直接回答，也可以选择工具。模型可能返回：

```text
content="..."，tool_calls=[]          -> 最终回答
content=None，tool_calls=[...]         -> 请求程序执行工具
```

一个 Tool Call 包含：

- `id`：本次调用的关联 ID；
- `function.name`：工具名；
- `function.arguments`：JSON 字符串，不是已经可信的字典。

客户端把 SDK 对象归一化成项目自己的 `AssistantDecision`。这样 Agent 循环不依赖供应商 SDK 的复杂类型，也方便测试。

客户端只对 timeout、连接问题、429 和 5xx 做有限重试。API Key 错误和参数错误原样重试不会恢复。

## 7. 第五层：Agent 控制循环

打开 `app/agent.py`，按下面顺序阅读 `run()`：

```text
初始化 System/User 消息
 -> 调用模型
 -> 保存完整 Assistant 消息
 -> 没有工具调用：返回最终答案
 -> 有工具调用：检查重复、执行、记录 trace
 -> 添加 role=tool 消息
 -> 进入下一步模型决策
```

### 为什么必须保存 Assistant 工具调用消息

工具结果不能孤立出现。消息历史必须保持关联：

```json
{"role": "assistant", "tool_calls": [{"id": "call-1", "...": "..."}]}
{"role": "tool", "tool_call_id": "call-1", "content": "..."}
```

`tool_call_id` 告诉模型这个结果对应哪一次请求。一次 Assistant 消息可以提出多个工具调用，每个 Tool 结果都要使用自己的 ID。

### 什么叫一步

本项目把“一次模型决策”定义为一步。模型在同一次回复中提出两个工具调用，这两个调用的 trace 都属于同一步。默认最多 5 步，而不是最多 5 个工具。

### 重复调用保护

Agent 将工具名和规范化 JSON 参数组成签名：

```text
("create_todo", {"title":"带外套"})
```

JSON 空格和键顺序不同不会绕过检查。重复签名不会再次执行，而是回传 `duplicate_tool_call`。这对创建待办等副作用工具尤其重要。

重复保护不等于完整幂等性。生产系统还可能需要业务幂等键、数据库唯一约束和调用状态表。

### 最大步骤

模型可能不断请求工具。没有上限会造成无限循环、费用增长和重复副作用。本项目到达 5 步后返回 `max_steps_exceeded`，并保留已有 trace。

## 8. 完整消息演进

以“上海低于 20 度就创建待办”为例：

```text
第 1 次模型请求
  System: 工具规则
  User: 条件任务

第 1 次模型响应
  Assistant tool_call: get_weather({city: 上海}), id=w1

第 2 次模型请求新增
  Assistant: 上面的 tool_call
  Tool: id=w1, temperature_c=18.2

第 2 次模型响应
  Assistant tool_call: create_todo(...), id=t1

第 3 次模型请求新增
  Assistant: 上面的 tool_call
  Tool: id=t1, todo id=...

第 3 次模型响应
  Assistant: 最终回答
```

关键点：条件判断发生在模型看到真实天气结果之后。应用程序没有硬编码“低于 20”这一业务条件，模型通过上下文决定下一步。

## 9. 任务级上下文与会话级上下文

前面的例子描述的是一次 `run()` 内部的任务级上下文：模型每次决定后，Agent 把 Assistant 和 Tool 消息追加到同一份列表，直到得到最终回答。

现在项目还提供了 `app/conversation.py` 中的 `Conversation`，用于跨多次 `run()` 复用消息历史。交互 CLI 只创建一次会话：

```python
conversation = Conversation()
while True:
    user_input = input("你：").strip()
    result = await runner.run(user_input, conversation=conversation)
```

因此第二轮请求会携带第一轮的完整消息：

```text
System
User: 北京现在多少度？
Assistant: tool_calls = get_weather(...)
Tool: tool_call_id = ...，temperature_c = 23.8
Assistant: 北京当前 23.8°C
User: 那需要带水吗？
```

这里的“完整保留”是学习阶段的刻意选择，便于观察协议和调试。它还不是长期记忆：程序退出后历史丢失，也没有 token 上限控制。生产系统通常需要会话 ID、持久化、滑动窗口或摘要，并要在发送前估算上下文成本。

`seen_calls` 仍然只在一次 `run()` 中创建。这样同一轮不会重复产生副作用，但用户在下一轮明确提出相同请求时不会被上一轮的去重状态错误拦截。

## 10. 如何测试概率性系统

单元测试不能依赖真实模型，因为结果不稳定、速度慢、需要网络且产生费用。`tests/test_agent.py` 使用 `SequenceModel` 依次返回确定的 `AssistantDecision`：

```text
第一次返回天气调用
第二次返回待办调用
第三次返回最终回答
```

测试的不是“Fake Model 聪不聪明”，而是我们的控制代码收到每种合法或错误决策后是否正确处理。

测试分层：

- 契约测试：字段范围和枚举；
- 工具测试：真实文件算法与受控 HTTP 响应；
- 注册表测试：工具查找、解析、校验、错误包装；
- 客户端测试：发送参数和 SDK 响应归一化；
- Agent 测试：消息顺序、循环、重复调用和停止；
- 手动集成：真实 DeepSeek 与真实 Open-Meteo。

Mock HTTP 响应不代表天气工具是假的，它只是把第三方网络从单元测试中隔离。手动集成探测负责验证真实网络兼容性。

## 11. 安全边界

当前三个工具的风险不同：

| 工具 | 主要风险 | 当前控制 |
| --- | --- | --- |
| 搜索笔记 | 越权读文件、上下文过大 | 固定目录、仅 `.md`、结果上限 |
| 查询天气 | 外部不可用、响应异常 | timeout、状态检查、安全错误 |
| 创建待办 | 重复写入、文件损坏 | 参数校验、重复保护、原子替换 |

System Prompt 是行为提示，不是权限系统。真正的安全边界必须在 Python 代码、文件路径、网络白名单和数据层实现。

不要给学习 Agent 添加任意 shell 或任意文件读写工具。若未来确实需要，至少要有沙箱、路径隔离、命令白名单、资源限制和人工确认。

## 12. 调试方法

遇到错误时按边界定位：

1. 没有 `tool_calls`：查看工具描述和用户意图是否明确；
2. `unknown_tool`：查看模型返回的工具名和注册表；
3. `invalid_arguments`：查看 Schema、原始参数和 Pydantic 错误字段；
4. `tool_execution_error`：单独运行工具，排查文件或网络；
5. 重复调用：检查上一次 Tool 结果是否清晰、Prompt 是否要求模型调整；
6. 最大步骤：画出每步消息，判断是否缺少终止信息；
7. 模型错误：区分可重试网络问题与认证、模型名等永久错误。

先用失败测试复现控制逻辑问题，再修实现。真实供应商问题则保存脱敏后的请求形状、错误类型和 request ID。

## 13. 动手练习

1. 修改 `max_steps` 为 2，运行多步条件任务并观察停止原因。
2. 让测试模型连续两次创建相同待办，解释为什么只执行一次。
3. 给 `CreateTodoArgs` 增加 `tags: list[str]`，同步 Schema、工具和测试。
4. 为 `search_notes` 增加标题加权，但仍限制返回数量。
5. 为天气工具增加湿度字段，同步请求参数、返回结构和测试响应。
6. 增加只读 `list_todos` 工具，并解释权限风险。
7. 给有副作用工具加入显式 `requires_confirmation` 元数据。
8. 构造非法日期和未知优先级，观察 `invalid_arguments` 如何回传。
9. 记录每次模型调用延迟和 token usage，估算一次多步任务成本。
10. 建立 10 条工具选择评估集，报告工具名和参数准确率。

## 14. 阶段验收

当你可以不看代码画出以下流程，并独立增加一个受控工具，就完成了第三阶段：

```text
Tool Schema -> DeepSeek -> tool_calls -> JSON/Pydantic 校验
-> Python handler -> Tool message/tool_call_id -> DeepSeek -> 最终回答
```

你还应能解释：

- 为什么模型不能直接执行函数；
- 为什么工具参数必须本地校验；
- 为什么 Tool 消息需要 `tool_call_id`；
- 最大步骤与重复调用保护分别解决什么问题；
- 哪些工具需要人工确认和幂等控制；
- 为什么单元测试不应该依赖真实模型。
