# 第二阶段目录重组设计

## 目标

把简历分析助手的讲义、应用代码、练习、示例、测试、评估数据和阶段文档集中到 `stages/phase2_resume_analysis/`，使阶段二可以独立阅读、安装、运行和测试。

## 目标结构

```text
stages/phase2_resume_analysis/
├── README.md
├── lesson.md
├── requirements.txt
├── .env.example
├── app/
├── examples/
├── exercises/
├── tests/
├── data/
└── docs/
```

`stages` 和阶段目录都是 Python 包。所有导入使用 `stages.phase2_resume_analysis...` 的绝对路径，所有命令从仓库根目录执行。

## 范围

移动当前 `phase2/`、`examples/`、`tests/test_phase2_*.py`、`phase2_exercise.py`、`test_phase2_exercise.py`、`eval_cases.jsonl`、第二阶段讲义、阶段二设计/计划、`.env.example` 和当前阶段依赖文件。根目录保留全局 README、学习路线、项目记忆以及阶段一文件。

用户新增且未跟踪的 `.vscode/`、`openai-cookbook-main/` 和 `openai-cookbook-main.zip` 不属于本次范围，不移动、不修改、不提交。

## 兼容与验证

移动后更新所有导入、文档路径和运行命令。增加根目录 `pytest.ini`，只把 `stages` 作为测试发现范围，避免第三方学习资料中的测试被误收集。验收包括阶段测试、根目录 pytest、编译检查、Mock 示例和评估数据加载。
