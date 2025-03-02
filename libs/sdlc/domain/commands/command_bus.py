"""Command bus for handling commands"""

from dataclasses import dataclass
from typing import Callable, Dict, Type
from uuid import UUID


@dataclass
class Command:
    """Base class for all commands"""

    command_id: UUID
    correlation_id: UUID


class CommandBus:
    """Command bus for routing commands to their handlers"""

    _handlers: Dict[Type[Command], Callable] = {}

    @classmethod
    def register(cls, command_type: Type[Command], handler: Callable) -> None:
        """Register a handler for a command type"""
        cls._handlers[command_type] = handler

    @classmethod
    def handle(cls, command: Command) -> None:
        """Handle a command by routing it to its registered handler"""
        handler = cls._handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for command type {type(command)}")
        handler(command)
