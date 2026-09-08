# Agent 学习项目记忆

> 更新时间：2026-09-07

## 项目目标

这是一个面向 Agent/LLM 应用开发实习准备的学习仓库。目标是在 3-6 个月内，通过可运行项目掌握 Python 工程、LLM 调用、结构化输出、Tool Calling、RAG、工作流、评估、FastAPI 服务化和 Docker 部署。

## 当前进度

- 阶段一基础工程：已有 FastAPI、异步和 Pydantic 示例。
- 阶段二讲义：已完成 5 节课，见 `lessons/phase-2-llm-structured-apps.md`。
- 阶段二第 1 课练习：已完成基础版本，见 `phase2_exercise.py`。
- 阶段二练习测试：见 `test_phase2_exercise.py`。
- 下一步：学习者扩展 `ResumeAnalysis` 字段并补充失败测试，然后进入真实 API、Prompt 和重试实现。

## 重要文件

| 文件 | 用途 |
| --- | --- |
| `docs/agent-learning-roadmap.md` | 16 周总路线、阶段验收和求职准备 |
| `lessons/phase-2-llm-structured-apps.md` | 第二阶段完整讲义 |
| `phase2_exercise.py` | Pydantic 结构化输出和 mock 模型练习 |
| `test_phase2_exercise.py` | 第一课成功/失败测试 |
| `main.py` | 现有 FastAPI 与异步处理示例 |
| `test_fastapi.py` | FastAPI 示例测试 |
| `test_pydantic.py` | Pydantic 校验示例 |

## 环境与运行

项目在 Windows + PowerShell 下开发，虚拟环境目录为 `agent_env`，Python 可执行文件为 `agent_env/Scripts/python.exe`。基础练习运行命令：

```powershell
.\agent_env\Scripts\python.exe phase2_exercise.py
```

测试依赖可能需要安装：

```powershell
.\agent_env\Scripts\python.exe -m pip install pytest
.\agent_env\Scripts\python.exe -m pytest -q
```

真实模型练习使用 DeepSeek 的 OpenAI 兼容 API。客户端默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-v4-pro`；可通过 `LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_USE_RESPONSE_FORMAT` 覆盖。只通过环境变量提供 `LLM_API_KEY`，不要把密钥写入仓库、日志或记忆文件。

## 学习约定

1. 先用 mock 完成单元测试，再接入真实网络 API。
2. 模型输出永远经过 JSON 解析和 Pydantic 校验，不能直接写入数据库或执行工具。
3. 网络调用必须有 timeout；只对临时错误做有限重试。
4. 每节课保留可运行代码、测试、README 更新和简短复盘。
5. 评估不仅记录平均分，还要保存 JSON 失败、字段缺失、幻觉、超时和供应商错误等失败样例。

## 跨设备恢复步骤

```powershell
git clone https://github.com/1saachen/agent-learning.git
cd agent-learning
Get-Content docs\project-memory.md
Get-Content lessons\phase-2-llm-structured-apps.md
python -m venv agent_env
.\agent_env\Scripts\python.exe -m pip install fastapi pydantic uvicorn pytest
.\agent_env\Scripts\python.exe phase2_exercise.py
```

虚拟环境不会提交到仓库，因此每台新设备都要单独创建。不要复制或提交本地 API Key。
