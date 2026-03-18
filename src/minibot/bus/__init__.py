"""Message bus for decoupled channel-agent communication."""

from minibot.bus.events import InboundMessage, OutboundMessage
from minibot.bus.message_bus import MessageBus

__all__ = ["InboundMessage", "OutboundMessage", "MessageBus"]
