from dataclasses import dataclass
from typing import Any


@dataclass
class Message:
    type: str   # "task", "result", "feedback", "control"
    sender: str
    receiver: str
    payload: Any

    def create_reply(self, payload: Any, msg_type: str = "result") -> "Message":
        return Message(
            type=msg_type,
            sender=self.receiver,
            receiver=self.sender,
            payload=payload,
        )

    def __repr__(self) -> str:
        payload_preview = str(self.payload)
        if len(payload_preview) > 80:
            payload_preview = payload_preview[:77] + "..."
        return f"Message({self.type}: {self.sender} -> {self.receiver}, payload={payload_preview})"