# Agent Learning

这是一个面向 Agent 开发实习准备的学习项目，包含学习路线、阶段讲义和可运行练习。

## 当前内容

- `docs/agent-learning-roadmap.md`：16 周 Agent 开发学习路线
- `docs/project-memory.md`：当前进度、约定和跨设备恢复步骤
- `lessons/phase-2-llm-structured-apps.md`：第二阶段讲义
- `phase2_exercise.py`：结构化 LLM 输出练习
- `test_phase2_exercise.py`：练习测试
- `phase2/`：第二阶段第 2-5 课的契约、Prompt、模型客户端、服务层和 FastAPI 代码
- `tests/`：第二阶段离线测试（不访问真实模型）

## 本地运行

```powershell
.\agent_env\Scripts\python.exe phase2_exercise.py
```

安装测试依赖后运行：

```powershell
.\agent_env\Scripts\python.exe -m pip install pytest
.\agent_env\Scripts\python.exe -m pytest -q
```

启动第二阶段 API（需要先设置 `LLM_API_KEY`、`LLM_MODEL`，可选 `LLM_BASE_URL`）：

```powershell
.\agent_env\Scripts\python.exe -m phase2.run_api
```

浏览器打开 `http://127.0.0.1:8000/docs` 查看接口文档。真实 API 调用只放在本地环境，测试使用 `FakeModelCaller`。
