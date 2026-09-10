# 简历分析助手阶段项目设计

## 目标

构建一个可以本地运行、使用 DeepSeek API、具备离线测试和基础评估能力的简历分析助手。用户提交简历和职位描述后，系统返回严格校验的摘要、匹配技能、缺失技能、匹配分、工作年限和面试问题。

## 范围

本次包含：Pydantic 输入/输出契约、Prompt 构造、DeepSeek OpenAI 兼容客户端、timeout/有限重试、JSON/Pydantic 解析、FastAPI 接口、命令行示例、离线 Mock 测试和评估数据。

本次不包含：用户登录、数据库、前端页面、文档上传、向量检索、多 Agent 和生产部署。这些属于后续阶段，避免阶段二项目失控。

## 模块边界

- `app/contracts.py`：只定义请求和响应数据结构。
- `app/prompts.py`：只定义 Prompt 版本和输入拼接规则。
- `app/client.py`：只负责模型调用和有限重试，不解析业务 JSON。
- `app/service.py`：编排 Prompt、模型调用、解析和诊断。
- `app/api.py`：把 HTTP 请求映射到服务层，并把内部错误转换为 502/504。
- `app/evaluation.py`：读取 JSONL 样例并计算离线技能命中指标。
- `examples/`：展示 Mock 和真实客户端的调用方式，不包含密钥。

## 数据流与错误处理

输入长度错误由 FastAPI/Pydantic 返回 422。模型超时、连接失败或有限重试耗尽返回 504。模型返回非法 JSON 或不符合契约返回 502。内部日志只保留错误类型和截断预览，不记录 API Key。

## 验证方式

所有网络调用都通过 `ModelCaller` 注入，测试使用 `FakeModelCaller`。测试覆盖输入边界、Prompt 数据位置、重试、结构化解析、API 错误映射和评估指标。真实 DeepSeek 请求只通过显式环境变量启动。
