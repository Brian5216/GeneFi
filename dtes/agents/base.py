"""Base Agent class for GeneFi multi-agent system."""
import uuid
import time
from typing import Optional
from dtes.protocol.a2a import A2AMessage, MessageType, MessageBus


class BaseAgent:
    """Base class for all GeneFi agents."""

    def __init__(self, agent_type: str, bus: MessageBus):
        self.agent_id = f"{agent_type}-{str(uuid.uuid4())[:6]}"
        self.agent_type = agent_type
        self.bus = bus
        self.created_at = time.time()
        self.message_log: list[A2AMessage] = []

        # Register on bus
        self.bus.subscribe(self.agent_id, self._on_message)

    async def _on_message(self, message: A2AMessage):
        """Handle incoming messages."""
        self.message_log.append(message)
        await self.handle_message(message)

    async def handle_message(self, message: A2AMessage):
        """Override in subclass to handle specific messages."""
        pass

    async def send(
        self,
        msg_type: MessageType,
        receiver: str,
        payload: dict,
        generation: int = 0,
        correlation_id: Optional[str] = None,
    ) -> A2AMessage:
        """Send a message through the bus."""
        msg = A2AMessage(
            msg_type=msg_type,
            sender=self.agent_id,
            receiver=receiver,
            payload=payload,
            generation=generation,
            correlation_id=correlation_id,
        )
        await self.bus.publish(msg)
        return msg

    def get_status(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "messages_processed": len(self.message_log),
            "uptime": time.time() - self.created_at,
        }
