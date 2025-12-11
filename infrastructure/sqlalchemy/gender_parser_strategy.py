"""
Concrete implementation of the gender parser strategy.
"""
from domain.strategies import IGenderParserStrategy
from helpers.enums.gender import Gender


class GenderParserStrategy(IGenderParserStrategy):
    """
    Standard implementation of gender parsing strategy.
    
    This strategy parses gender values by:
    - Returning Gender enums as-is
    - Converting string values to Gender by value (e.g., "male" -> Gender.MALE)
    - Converting string names to Gender by name (e.g., "MALE" -> Gender.MALE)
    - Raising ValueError for invalid values
    """

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
        if isinstance(value, Gender):
            return value
        if isinstance(value, str):
            try:
                return Gender(value)
            except ValueError:
                try:
                    return Gender[value.upper()]
                except KeyError:
                    pass
        accepted_values = ", ".join([g.value for g in Gender])
        raise ValueError(f"Gènere no vàlid. Valors acceptats: {accepted_values}.")
