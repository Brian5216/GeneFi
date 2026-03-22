"""A2A (Agent-to-Agent) Communication Protocol.

Standardized JSON message format for all inter-agent communication.
Every message is logged for full audit trail compliance.
"""
import uuid
import time
import json
import os
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from config import Config


class MessageType(str, Enum):
    # Predictor → Executor
    STRATEGY_BATCH = "strategy_batch"
    # Executor → Judge
    EXECUTION_REPORT = "execution_report"
    # Judge → Predictor
    EVOLUTION_DIRECTIVE = "evolution_directive"
    # Judge → System
    RISK_ALERT = "risk_alert"
    SAFE_MODE_TRIGGER = "safe_mode_trigger"
    # System broadcasts
    MARKET_UPDATE = "market_update"
    GENERATION_START = "generation_start"
    GENERATION_END = "generation_end"


@dataclass
class A2AMessage:
    """Standardized Agent-to-Agent message."""
    msg_type: MessageType
    sender: str          # Agent ID (e.g., "predictor-001")
    receiver: str        # Agent ID or "broadcast"
    payload: dict = field(default_factory=dict)
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    generation: int = 0
    correlation_id: Optional[str] = None  # Links related messages

    def to_dict(self) -> dict:
        d = asdict(self)
        d["msg_type"] = self.msg_type.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(d: dict) -> "A2AMessage":
        d["msg_type"] = MessageType(d["msg_type"])
        return A2AMessage(**d)


class MessageBus:
    """Central message bus for A2A communication with audit logging."""

    def __init__(self):
        self.messages: list[A2AMessage] = []
        self._subscribers: dict[str, list] = {}  # agent_id -> [callback]
        self._global_subscribers: list = []

    def subscribe(self, agent_id: str, callback):
        if agent_id not in self._subscribers:
            self._subscribers[agent_id] = []
        self._subscribers[agent_id].append(callback)

    def subscribe_all(self, callback):
        self._global_subscribers.append(callback)

    async def publish(self, message: A2AMessage):
        """Publish a message to the bus."""
        self.messages.append(message)
        self._log_message(message)

        # Deliver to specific receiver
        if message.receiver in self._subscribers:
            for cb in self._subscribers[message.receiver]:
                result = cb(message)
                if hasattr(result, "__await__"):
                    await result

        # Broadcast messages go to all
        if message.receiver == "broadcast":
            for agent_id, callbacks in self._subscribers.items():
                if agent_id != message.sender:
                    for cb in callbacks:
                        result = cb(message)
                        if hasattr(result, "__await__"):
                            await result

        # Global subscribers always receive
        for cb in self._global_subscribers:
            result = cb(message)
            if hasattr(result, "__await__"):
                await result

    def get_messages(
        self,
        msg_type: Optional[MessageType] = None,
        sender: Optional[str] = None,
        generation: Optional[int] = None,
        limit: int = 100,
    ) -> list[A2AMessage]:
        """Query messages with filters."""
        filtered = self.messages
        if msg_type:
            filtered = [m for m in filtered if m.msg_type == msg_type]
        if sender:
            filtered = [m for m in filtered if m.sender == sender]
        if generation is not None:
            filtered = [m for m in filtered if m.generation == generation]
        return filtered[-limit:]

    def _log_message(self, message: A2AMessage):
        """Append message to audit log."""
        log_dir = Config.LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "a2a_messages.jsonl")
        with open(log_file, "a") as f:
            f.write(message.to_json().replace("\n", " ") + "\n")
