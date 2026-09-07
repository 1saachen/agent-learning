# Agent 开发实习学习路线

## 目标与使用方式

这条路线面向有 Python 基础、希望在 3-6 个月内申请初级 Agent/LLM 应用开发实习的人。每周投入建议为 12-20 小时。学习原则是：每个阶段都产出可运行代码、测试、README 和复盘，而不是只看课程。

最终应具备：模型 API 调用、结构化输出、Tool Calling、RAG、工作流编排、评估、FastAPI 服务化、Docker 部署和基本安全意识。

## 技术栈

- Python、`asyncio`、类型注解、pytest
- FastAPI、Pydantic、SQLite/PostgreSQL、Redis
- OpenAI 兼容 API、Embedding、向量数据库（Chroma/Qdrant/pgvector 任选）
- LangChain 用于组件理解，LangGraph 用于有状态工作流
- Git、Docker、Linux 基础、GitHub Actions

## 16 周路线

| 周次 | 主题 | 必须产出 |
| --- | --- | --- |
| 1-2 | Python 工程与 FastAPI | 文档问答 API 雏形、日志、异常处理、接口测试 |
| 3-4 | LLM 与结构化应用 | 简历分析助手、Pydantic 输出校验、失败重试、10 条测试集 |
| 5-7 | Tool Calling 与单 Agent | 个人研究助手，支持搜索、笔记、天气、待办等工具 |
| 8-10 | RAG 知识库 | 多文档企业知识库、引用来源、20-30 条评估集 |
| 11-13 | 工作流与状态 | 技术调研报告 Agent，含拆解、并行检索、人工确认 |
| 14-16 | 工程化与求职 | Docker 部署、限流/超时/成本控制、简历与面试材料 |

## 各阶段验收

### 阶段一：基础工程

能够解释 HTTP、异步、Pydantic、数据库和日志；完成一个可启动的 FastAPI 服务，并为成功、参数错误和异常路径写测试。

### 阶段二：LLM 与结构化输出

完成 `lessons/phase-2-llm-structured-apps.md` 中的简历分析助手。输出必须经过 Pydantic 校验；模型调用要有超时、重试和脱敏日志；至少有 10 条固定测试样例。

### 阶段三：工具与 Agent

能画出模型选择工具、代码执行工具、结果回传和最终回答的完整流程；设置最大步骤数、工具参数校验、权限和超时。

### 阶段四：RAG

能说明 Chunk、Embedding、Top-K、混合检索、Rerank 的作用；回答带引用；对知识库没有依据的问题拒答；用测试集报告召回和回答质量。

### 阶段五：工作流

能用状态、节点、条件分支、循环、中断恢复和人工确认构建多步骤流程，并记录每次运行轨迹。

### 阶段六：工程化

能用 Docker 启动服务，配置环境变量，处理超时/重试/幂等/限流，识别 Prompt Injection、SSRF 和敏感信息泄漏风险。

## 三个作品集项目

1. **结构化 LLM 应用**：简历分析或邮件分类。展示 Prompt、JSON Schema、Pydantic、错误恢复和测试集。
2. **企业知识库 RAG**：支持文档上传、索引、引用、历史记录和评估页面。
3. **技术调研 Agent**：任务拆解、并行搜索、来源检查、人工确认、报告生成和运行日志。

每个项目 README 至少包含：背景、功能、架构图、核心流程、技术选型、测试/评估结果、已知问题和启动方式。简历中写“做了什么”和“如何验证”，不要只写使用了哪个框架。

## 面试清单

- Python：数据结构、异常、生成器、装饰器、异步、类型注解
- 后端：HTTP、REST、FastAPI、事务、索引、Redis、JWT、Docker
- LLM：Token、上下文、Temperature、Embedding、RAG、Tool Calling、幻觉、Prompt Injection、成本和延迟
- 系统设计：Agent 无限循环、工具权限、模型输出格式错误、失败重试、评估指标、何时不该使用 Agent

## 每周节奏

概念 20%，官方文档/源码 15%，编码 45%，测试与调试 10%，README 和复盘 10%。每周至少一次 Git 提交、一个可运行功能、一组测试和一段复盘。

