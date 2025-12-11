"""
Unit tests for the GenderParserStrategy.
"""
import pytest
from helpers.enums.gender import Gender
from infrastructure.sqlalchemy.gender_parser_strategy import GenderParserStrategy


class TestGenderParserStrategy:
    """Test suite for GenderParserStrategy."""

    def test_parse_gender_enum_returns_same_enum(self):
        """Test that passing a Gender enum returns the same enum."""
        parser = GenderParserStrategy()
        result = parser.parse(Gender.MALE)
        assert result == Gender.MALE
        assert isinstance(result, Gender)

    def test_parse_gender_enum_female(self):
        """Test parsing Gender.FEMALE enum."""
        parser = GenderParserStrategy()
        result = parser.parse(Gender.FEMALE)
        assert result == Gender.FEMALE

    def test_parse_gender_enum_others(self):
        """Test parsing Gender.OTHERS enum."""
        parser = GenderParserStrategy()
        result = parser.parse(Gender.OTHERS)
        assert result == Gender.OTHERS

    def test_parse_gender_string_value_male(self):
        """Test parsing string value 'male'."""
        parser = GenderParserStrategy()
        result = parser.parse("male")
        assert result == Gender.MALE

    def test_parse_gender_string_value_female(self):
        """Test parsing string value 'female'."""
        parser = GenderParserStrategy()
        result = parser.parse("female")
        assert result == Gender.FEMALE

    def test_parse_gender_string_value_others(self):
        """Test parsing string value 'others'."""
        parser = GenderParserStrategy()
        result = parser.parse("others")
        assert result == Gender.OTHERS

    def test_parse_gender_string_name_male(self):
        """Test parsing string name 'MALE'."""
        parser = GenderParserStrategy()
        result = parser.parse("MALE")
        assert result == Gender.MALE

    def test_parse_gender_string_name_female(self):
        """Test parsing string name 'FEMALE'."""
        parser = GenderParserStrategy()
        result = parser.parse("FEMALE")
        assert result == Gender.FEMALE

    def test_parse_gender_string_name_others(self):
        """Test parsing string name 'OTHERS'."""
        parser = GenderParserStrategy()
        result = parser.parse("OTHERS")
        assert result == Gender.OTHERS

    def test_parse_gender_string_name_lowercase_to_uppercase(self):
        """Test parsing lowercase string names like 'male' that fallback to uppercase."""
        parser = GenderParserStrategy()
        # This tests the fallback to Gender[value.upper()]
        result = parser.parse("Male")
        assert result == Gender.MALE

    def test_parse_gender_invalid_string_raises_value_error(self):
        """Test that parsing an invalid string raises ValueError."""
        parser = GenderParserStrategy()
        with pytest.raises(ValueError) as exc_info:
            parser.parse("invalid_gender")
        assert "Gènere no vàlid" in str(exc_info.value)
        assert "male, female, others" in str(exc_info.value)

    def test_parse_gender_invalid_type_raises_value_error(self):
        """Test that passing a non-string, non-Gender type raises ValueError."""
        parser = GenderParserStrategy()
        with pytest.raises((ValueError, KeyError)):
            parser.parse(123)  # type: ignore

    def test_parse_gender_none_raises_error(self):
        """Test that passing None raises an error."""
        parser = GenderParserStrategy()
        with pytest.raises((ValueError, KeyError, AttributeError)):
            parser.parse(None)  # type: ignore

    def test_parse_gender_empty_string_raises_value_error(self):
        """Test that parsing an empty string raises ValueError."""
        parser = GenderParserStrategy()
        with pytest.raises((ValueError, KeyError)):
            parser.parse("")
