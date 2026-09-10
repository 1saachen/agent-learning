# Agent 学习项目记忆

> 更新时间：2026-09-10

## 项目目标

这是一个面向 Agent/LLM 应用开发实习准备的学习仓库。目标是在 3-6 个月内，通过可运行项目掌握 Python 工程、LLM 调用、结构化输出、Tool Calling、RAG、工作流、评估、FastAPI 服务化和 Docker 部署。

## 当前进度

- 阶段一基础工程：已有 FastAPI、异步和 Pydantic 示例。
- 阶段二全部内容已集中到 `stages/phase2_resume_analysis/`。
- 阶段二讲义：`stages/phase2_resume_analysis/lesson.md`。
- 阶段二核心知识手册：`stages/phase2_resume_analysis/docs/phase2-core-knowledge-guide.md`。
- 阶段项目代码、示例、练习、测试和评估数据均位于该阶段目录下。
- 已跑通 DeepSeek 简历分析项目，并完成项目代码的基础阅读和理解。
- 下一步：对照核心知识手册完成掌握度检查表，并至少完成两个进阶实验，再进入阶段三。

## 重要文件

| 文件 | 用途 |
| --- | --- |
| `docs/agent-learning-roadmap.md` | 16 周总路线、阶段验收和求职准备 |
| `stages/phase2_resume_analysis/lesson.md` | 第二阶段完整讲义 |
| `stages/phase2_resume_analysis/docs/phase2-core-knowledge-guide.md` | LLM、Prompt 与结构化输出核心知识手册 |
| `stages/phase2_resume_analysis/app/` | 简历分析应用代码 |
| `stages/phase2_resume_analysis/exercises/` | 第一课练习和测试 |
| `main.py` | 现有 FastAPI 与异步处理示例 |
| `test_fastapi.py` | FastAPI 示例测试 |
| `test_pydantic.py` | Pydantic 校验示例 |
| `stages/phase2_resume_analysis/app/evaluation.py` | JSONL 评估样例加载、技能命中率和聚合指标 |
| `stages/phase2_resume_analysis/examples/` | Mock、真实 DeepSeek 和批量评估入口 |
| `stages/phase2_resume_analysis/data/eval_cases.jsonl` | 阶段项目评估数据 |

## 环境与运行

项目在 Windows + PowerShell 下开发，虚拟环境目录为 `agent_env`，Python 可执行文件为 `agent_env/Scripts/python.exe`。基础练习运行命令：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.exercises.phase2_exercise
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.mock_resume_analysis
```

测试依赖可能需要安装：

```powershell
.\agent_env\Scripts\python.exe -m pip install pytest
.\agent_env\Scripts\python.exe -m pytest -q
```

完整依赖也可以使用：`.\\agent_env\\Scripts\\python.exe -m pip install -r stages\\phase2_resume_analysis\\requirements.txt`。

真实模型练习使用 DeepSeek 的 OpenAI 兼容 API。客户端默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-v4-pro`，并自动读取电脑环境变量 `DEEPSEEK_API_KEY`；可通过 `LLM_BASE_URL`、`LLM_MODEL` 和 `LLM_USE_RESPONSE_FORMAT` 覆盖。不要把密钥写入仓库、日志或记忆文件。`.env.example` 只包含占位值。

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
Get-Content stages\phase2_resume_analysis\lesson.md
Get-Content stages\phase2_resume_analysis\docs\phase2-core-knowledge-guide.md
python -m venv agent_env
.\agent_env\Scripts\python.exe -m pip install -r stages\phase2_resume_analysis\requirements.txt
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.exercises.phase2_exercise
```

虚拟环境不会提交到仓库，因此每台新设备都要单独创建。不要复制或提交本地 API Key。
