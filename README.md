# Agent Learning

这是一个面向 Agent 开发实习准备的学习项目，包含学习路线、阶段讲义和可运行练习。

## 学习阶段

- `docs/agent-learning-roadmap.md`：16 周 Agent 开发学习路线
- `docs/project-memory.md`：当前进度、约定和跨设备恢复步骤
- `stages/phase2_resume_analysis/`：第二阶段简历分析助手的讲义、代码、练习、测试和评估数据
- `stages/phase2_resume_analysis/docs/phase2-core-knowledge-guide.md`：LLM、Prompt 与结构化输出核心知识手册

## 本地运行

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.exercises.phase2_exercise
```

安装第二阶段依赖后运行：

```powershell
.\agent_env\Scripts\python.exe -m pip install -r stages\phase2_resume_analysis\requirements.txt
.\agent_env\Scripts\python.exe -m pytest -q
```

先运行不产生 API 费用的完整链路示例：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.mock_resume_analysis
```

启动第二阶段 DeepSeek API（客户端会自动读取电脑环境变量 `DEEPSEEK_API_KEY`；模型默认是 `deepseek-v4-pro`，可选覆盖 `LLM_MODEL` 和 `LLM_BASE_URL`）：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.app.run_api
```

DeepSeek 默认地址为 `https://api.deepseek.com`。如果当前模型支持 JSON 模式，可在电脑环境变量中设置 `LLM_USE_RESPONSE_FORMAT=true`；默认关闭，仍由 Prompt 和 Pydantic 校验约束输出。无需在每次启动前用终端设置 API Key。


真实 DeepSeek 单次调用和批量评估：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.deepseek_resume_analysis
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.evaluate_deepseek
```

调用接口示例：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/resume/analyze -Method Post -ContentType 'application/json' -Body (@{
  resume = 'Python backend developer with FastAPI and PostgreSQL experience.'
  job_description = 'Backend intern who should build Python APIs and learn Docker.'
} | ConvertTo-Json)
```

浏览器打开 `http://127.0.0.1:8000/docs` 查看接口文档。真实 API 调用只放在本地环境，测试使用 `FakeModelCaller`。
