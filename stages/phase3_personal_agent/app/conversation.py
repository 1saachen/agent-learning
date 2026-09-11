from typing import Any

from .prompts import SYSTEM_PROMPT


class Conversation:
    """Owns the complete short-term message history for one conversation."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self._messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self._messages

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_message(self, message: dict[str, Any]) -> None:
        self._messages.append(message)

    def add_tool_message(
        self,
        *,
        tool_call_id: str,
        name: str,
        content: str,
    ) -> None:
        self._messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content,
            }
        )
