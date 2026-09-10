# 第三阶段：个人研究助手

这是一个使用原生 Python 和 DeepSeek Tool Calling 实现的单 Agent。它不依赖 LangChain，目的是把“模型提出工具调用，程序验证并执行，再把结果返回模型”的完整协议展示清楚。

## 功能

- `search_notes`：搜索 `data/notes/*.md` 中的本地笔记；
- `get_weather`：通过 Open-Meteo 查询城市当前天气；
- `create_todo`：将待办写入 `data/todos.json`；
- 最多执行 5 个模型步骤；
- Pydantic 校验所有模型生成的工具参数；
- 拦截相同工具和参数的重复调用；
- 展示工具名、参数、结果、耗时和停止原因。

## 目录

```text
phase3_personal_agent/
├── app/
│   ├── contracts.py     # 参数、模型决策、工具结果和轨迹契约
│   ├── client.py        # DeepSeek Tool Calling 客户端
│   ├── registry.py      # 工具 Schema、参数校验和统一执行
│   ├── agent.py         # Agent 控制循环
│   ├── prompts.py       # System Prompt
│   └── tools/           # 笔记、待办、天气工具
├── data/                # 本地笔记和待办数据
├── examples/run_agent.py
├── tests/               # 不调用真实模型的离线测试
├── lesson.md            # 按代码阅读顺序学习
└── docs/phase3-core-knowledge-guide.md
```

## 安装

在仓库根目录执行：

```powershell
.\agent_env\Scripts\python.exe -m pip install -r stages\phase3_personal_agent\requirements.txt
```

程序自动读取电脑环境变量 `DEEPSEEK_API_KEY`，不需要在每次终端会话中重新设置。默认配置：

```text
Base URL: https://api.deepseek.com
Model:    deepseek-v4-pro
```

可以通过电脑环境变量 `LLM_BASE_URL` 和 `LLM_MODEL` 覆盖默认值。不要把 API Key 写进代码、Prompt、测试、日志或 Git。

Open-Meteo 天气接口不需要 API Key，但运行时需要能访问互联网。

## 运行

交互模式：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase3_personal_agent.examples.run_agent
```

单次模式：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase3_personal_agent.examples.run_agent --prompt "查询上海当前天气"
```

建议依次尝试：

```text
搜索我的笔记，告诉我 Tool Calling 是什么。

查询上海当前天气。

创建一个标题为“复习 Agent 循环”的高优先级待办，截止日期是 2026-09-15。

查询上海当前天气。如果温度低于 20 摄氏度，创建一个标题为“出门带外套”的高优先级待办；否则只告诉我天气。
```

最后一个请求最适合观察多步 Agent：模型先查询天气，看到工具结果后，再决定是否创建待办。

## 测试

运行阶段三测试：

```powershell
.\agent_env\Scripts\python.exe -m pytest stages\phase3_personal_agent -q
```

运行整个仓库测试：

```powershell
.\agent_env\Scripts\python.exe -m pytest -q
```

自动化测试使用可注入的 Fake Model Client 和受控 HTTP 响应，不调用 DeepSeek 或 Open-Meteo，不产生模型费用，也不会写入真实 `data/todos.json`。

## 数据和副作用

- 笔记工具只读取 `data/notes/` 第一层的 `.md` 文件；模型不能传入文件路径。
- 待办工具只写入 `data/todos.json`，并使用临时文件原子替换。
- `create_todo` 有真实副作用。运行相关请求后应检查该文件。
- 天气工具会向 Open-Meteo 发送城市名和经纬度请求。
- 执行轨迹不会输出 API Key，但会显示工具参数。不要把敏感信息放入工具参数。

## 学习顺序

1. 阅读 [lesson.md](lesson.md)；
2. 先看 `app/contracts.py` 和三个工具；
3. 再看 `app/registry.py`，理解 Schema、校验和执行的边界；
4. 看 `app/client.py`，理解 DeepSeek 返回的 `tool_calls`；
5. 最后逐行跟踪 `app/agent.py`；
6. 对照 `tests/test_agent.py` 手动画消息历史；
7. 使用 [核心知识手册](docs/phase3-core-knowledge-guide.md) 自测和准备面试。

## 已知限制

- 每次 `run()` 都是独立会话，没有长期记忆；
- 笔记搜索是简单文本匹配，不是 RAG；
- 待办文件没有并发写锁，不适合多进程服务；
- 天气只取 geocoding 的第一个城市结果，重名城市可能需要更具体的输入；
- 工具当前按顺序执行，没有并行调度；
- 没有认证、权限系统、数据库和生产监控；
- DeepSeek 模型是否正确选择工具仍是概率行为，需要评估集验证。

这些限制属于后续 RAG、工作流和工程化阶段的学习内容。
