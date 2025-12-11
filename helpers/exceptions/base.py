from __future__ import annotations

from typing import Optional


class ApplicationException(Exception):
    """Base class for custom application exceptions that standardizes the message handling."""

    def __init__(self, message: Optional[str] = None) -> None:
        default_message = self.__class__.__doc__
        if default_message:
            default_message = default_message.strip()
        final_message = (message or default_message or self.__class__.__name__)
        self.message = final_message
        super().__init__(final_message)

    def __str__(self) -> str:
        return self.message
