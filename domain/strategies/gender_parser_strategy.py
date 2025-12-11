"""
Strategy interface for parsing gender values.
"""
from abc import ABC, abstractmethod
from helpers.enums.gender import Gender


class IGenderParserStrategy(ABC):
    """
    Interface for strategies that parse gender values.
    
    Implementors of this interface provide strategies for converting
    various gender representations (string, enum) into the Gender enum type.
    """

    @abstractmethod
    def parse(self, value: Gender | str) -> Gender:
        """
        Parse a gender value and convert it to the Gender enum.

        Args:
            value: Gender value as either a Gender enum or string representation.
                   Strings can be either the enum value (e.g., "male") or name (e.g., "MALE").

        Returns:
            Gender: The parsed Gender enum value.

        Raises:
            ValueError: If the value cannot be parsed as a valid Gender.
        """
        raise NotImplementedError()
