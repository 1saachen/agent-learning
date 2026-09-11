import argparse
import asyncio

from ..app.agent import AgentRunner
from ..app.client import DeepSeekChatClient, ModelConfigurationError
from ..app.conversation import Conversation
from ..app.contracts import AgentRunResult, TraceEntry
from ..app.registry import build_default_registry


def build_runner(*, api_key: str | None = None) -> AgentRunner:
    return AgentRunner(
        DeepSeekChatClient(api_key=api_key),
        build_default_registry(),
        max_steps=5,
    )


def print_trace(trace: list[TraceEntry]) -> None:
    if not trace:
        print("\n执行轨迹：本次未调用工具。")
        return
    print("\n执行轨迹：")
    for entry in trace:
        status = "成功" if entry.ok else "失败"
        print(
            f"- 步骤 {entry.step} | {entry.tool_name} | {status} | "
            f"{entry.duration_ms:.2f} ms | {entry.summary}"
        )
        print(f"  参数：{entry.arguments}")


def print_result(result: AgentRunResult) -> None:
    print(f"\n助手：{result.answer}")
    print(f"停止原因：{result.stop_reason}；模型步骤：{result.steps}")
    print_trace(result.trace)


async def _run_once(
    runner: AgentRunner,
    user_input: str,
    *,
    conversation: Conversation | None = None,
) -> None:
    result = await runner.run(user_input, conversation=conversation)
    print_result(result)


async def main(prompt: str | None = None) -> None:
    try:
        runner = build_runner()
    except ModelConfigurationError as exc:
        print(f"配置错误：{exc}")
        return

    if prompt:
        await _run_once(runner, prompt)
        return

    conversation = Conversation()
    print("第三阶段个人研究助手。输入 exit 退出。")
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        await _run_once(runner, user_input, conversation=conversation)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 DeepSeek 个人研究助手")
    parser.add_argument("--prompt", help="执行一次请求后退出")
    args = parser.parse_args()
    asyncio.run(main(args.prompt))
