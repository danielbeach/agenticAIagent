from dataclasses import dataclass, field
from typing import List

@dataclass
class ConversationState:
    messages: List[str] = field(default_factory=list)
    def append(self, role: str, content: str):
        self.messages.append(f"{role.upper()}: {content}")
    def render(self) -> str:
        return "\n".join(self.messages[-30:])