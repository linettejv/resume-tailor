"""A fake Anthropic client that replays scripted responses, so tests cost nothing."""
from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace


def text(t: str):
    return SimpleNamespace(type="text", text=t)


def tool_use(id: str, name: str, input: dict):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


def response(*blocks, stop_reason: str = "tool_use"):
    return SimpleNamespace(
        content=list(blocks), stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )


@dataclass
class FakeClient:
    scripted: list
    calls: list = field(default_factory=list)  # snapshot of `messages` sent on each call

    def __post_init__(self):
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        self.calls.append([dict(m) for m in kwargs["messages"]])
        if not self.scripted:
            raise AssertionError("Agent called the API more times than the test scripted")
        return self.scripted.pop(0)
