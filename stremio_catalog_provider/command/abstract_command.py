from abc import ABC, abstractmethod
from typing import Any, Callable
import click

class AbstractCommand(ABC):
    """Abstract base class for all Click CLI commands in the application."""

    command_name: str = "command"

    def register_options(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Override this method to register click options/arguments on the command."""
        return fn

    @abstractmethod
    def run(self, **kwargs: Any) -> None:
        """The actual command execution logic."""
        pass

    def to_click_command(self) -> click.Command:
        """Converts the instance into a Click Command object."""
        @click.command(name=self.command_name)
        @self.register_options
        def command(**kwargs: Any) -> None:
            self.run(**kwargs)
        return command
