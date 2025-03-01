"""Command bus for handling commands"""
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar('T')


class CommandBus:
    """Simple command bus for routing commands to handlers"""
    _handlers: Dict[Any, Callable] = {}

    @classmethod
    def register(cls, command_type: Type[T], handler: Callable[[T], Any]) -> None:
        """Register a handler for a command type"""
        cls._handlers[command_type] = handler

    @classmethod
    def handle(cls, command: Any) -> Any:
        """Handle a command by routing it to the appropriate handler"""
        handler = cls._handlers.get(type(command))
        if not handler:
            raise ValueError(f"No handler registered for {type(command).__name__}")
        return handler(command) 