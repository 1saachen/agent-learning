# 会话上下文设计

## 目标

让阶段三 CLI 在同一进程内支持连续多轮对话，同时完整保留模型交互消息，方便学习和调试 Agent 的消息演进。

## 范围

- 新增独立的 `Conversation` 对象管理消息历史。
- 同一 `Conversation` 内保存 system、user、assistant（包括 `tool_calls`）和 tool 消息。
- `AgentRunner.run(user_input, conversation=...)` 支持复用会话。
- 不传 `conversation` 时继续执行一次性独立任务，兼容已有调用方。
- CLI 启动时创建一个会话，并在输入循环中复用它。
- `seen_calls` 只属于单次 `run()`，不同轮次不会互相误判重复。

## 非目标

- 不做磁盘或数据库持久化。
- 不做 token 预算、历史裁剪或摘要。
- 不实现多个用户或多个会话的服务端管理。

## 消息流

```text
Conversation.messages
  -> append user message
  -> model decision
  -> append assistant message
  -> append tool results
  -> next model decision
  -> append final assistant message
```

`Conversation` 只负责消息历史，不负责模型调用、工具执行或重复调用判断。Agent 仍然负责一次任务的控制循环；会话负责跨轮次共享消息。

## 失败行为

如果模型调用失败，已经追加的用户、assistant 工具调用和 tool 结果仍保留。这样可以在下一轮继续观察或调试，而不会隐式丢失已发生的交互。

## 验收标准

1. 第二轮模型请求包含第一轮的 user 和最终 assistant 消息。
2. 发生工具调用时，第二轮包含对应 assistant `tool_calls` 和 `tool_call_id` 匹配的 tool 消息。
3. 两个不同会话互不共享消息。
4. 不传会话时，现有单次任务行为和测试继续通过。
5. CLI 交互循环复用同一个会话对象。
