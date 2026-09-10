# 第二阶段：简历分析助手

本目录包含第二阶段的全部讲义、代码、练习、测试和评估数据。所有命令都从仓库根目录 `E:\Learning\agent` 执行。

## 目录

```text
phase2_resume_analysis/
├── lesson.md          # 完整讲义
├── requirements.txt  # 阶段依赖
├── .env.example       # DeepSeek 配置示例，不包含真实密钥
├── app/               # 契约、Prompt、客户端、服务、API、评估
├── examples/          # Mock、真实 DeepSeek、批量评估
├── exercises/         # 第一课练习及测试
├── tests/             # 项目离线测试
├── data/              # JSONL 评估样例
└── docs/              # 阶段设计和实现计划
```

## 安装与测试

```powershell
.\agent_env\Scripts\python.exe -m pip install -r stages\phase2_resume_analysis\requirements.txt
.\agent_env\Scripts\python.exe -m pytest stages\phase2_resume_analysis -q
```

## 运行

离线 Mock：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.mock_resume_analysis
```

真实 DeepSeek：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.deepseek_resume_analysis
```

启动 FastAPI：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.app.run_api
```

打开 `http://127.0.0.1:8000/docs`。客户端自动读取电脑环境变量 `DEEPSEEK_API_KEY`，默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-v4-pro`。

批量评估：

```powershell
.\agent_env\Scripts\python.exe -m stages.phase2_resume_analysis.examples.evaluate_deepseek
```
