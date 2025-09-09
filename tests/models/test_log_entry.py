"""Tests for the LogEntry class."""

import json
import math
from datetime import datetime
from types import NoneType

import pytest

from juffi.models.log_entry import MISSING, LogEntry


class TestLogEntryInitialization:
    """Test LogEntry initialization and JSON parsing."""

    def test_valid_json_initialization(self) -> None:
        """Test LogEntry initialization with valid JSON."""
        json_line = '{"level": "info", "message": "test message", "service": "api"}'
        entry = LogEntry(json_line, 42)

        assert entry.raw_line == json_line
        assert entry.line_number == 42
        assert entry.is_valid_json is True
        assert entry.data == {
            "level": "info",
            "message": "test message",
            "service": "api",
        }
        assert entry.level == "info"
        assert entry.timestamp is None

    def test_invalid_json_initialization(self) -> None:
        """Test LogEntry initialization with invalid JSON."""
        plain_text = "This is a plain text log entry"
        entry = LogEntry(plain_text, 10)

        assert entry.raw_line == plain_text
        assert entry.line_number == 10
        assert entry.is_valid_json is False
        assert entry.data == {"message": plain_text}
        assert entry.level is None
        assert entry.timestamp is None

    def test_non_dict_json_initialization(self) -> None:
        """Test LogEntry initialization with JSON that's not a dictionary."""
        json_array = '["item1", "item2", "item3"]'
        entry = LogEntry(json_array, 5)

        assert entry.raw_line == json_array
        assert entry.line_number == 5
        assert entry.is_valid_json is False
        assert entry.data == {"message": json_array}

    def test_empty_line_initialization(self) -> None:
        """Test LogEntry initialization with empty line."""
        entry = LogEntry("", 1)

        assert entry.raw_line == ""
        assert entry.line_number == 1
        assert entry.is_valid_json is False
        assert entry.data == {"message": ""}

    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is stripped from raw_line."""
        json_line = '  {"level": "info"}  \n'
        entry = LogEntry(json_line, 1)

        assert entry.raw_line == '{"level": "info"}'
        assert entry.is_valid_json is True

    def test_malformed_json_initialization(self) -> None:
        """Test LogEntry initialization with malformed JSON."""
        malformed_json = '{"level": "info", "message": "incomplete'
        entry = LogEntry(malformed_json, 3)

        assert entry.raw_line == malformed_json
        assert entry.line_number == 3
        assert entry.is_valid_json is False
        assert entry.data == {"message": malformed_json}


class TestLogEntryTimestampParsing:
    """Test timestamp parsing functionality."""

    def test_timestamp_field_parsing(self) -> None:
        """Test parsing timestamp from 'timestamp' field."""
        json_line = '{"level": "info", "timestamp": "2023-01-15T10:30:45.123"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 1
        assert entry.timestamp.day == 15
        assert entry.timestamp.hour == 10
        assert entry.timestamp.minute == 30
        assert entry.timestamp.second == 45

    def test_time_field_parsing(self) -> None:
        """Test parsing timestamp from 'time' field."""
        json_line = '{"level": "info", "time": "2023-02-20 14:25:30"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 2
        assert entry.timestamp.day == 20

    def test_at_timestamp_field_parsing(self) -> None:
        """Test parsing timestamp from '@timestamp' field."""
        json_line = '{"level": "info", "@timestamp": "2023-03-10T08:15:22"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 3
        assert entry.timestamp.day == 10

    def test_datetime_field_parsing(self) -> None:
        """Test parsing timestamp from 'datetime' field."""
        json_line = '{"level": "info", "datetime": "2023-04-05T16:45:10.500"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 4
        assert entry.timestamp.day == 5

    def test_date_field_parsing(self) -> None:
        """Test parsing timestamp from 'date' field."""
        json_line = '{"level": "info", "date": "2023-05-12T12:00:00"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023
        assert entry.timestamp.month == 5
        assert entry.timestamp.day == 12

    def test_timestamp_priority_order(self) -> None:
        """Test that timestamp fields are parsed in priority order."""
        # timestamp should take priority over time
        json_line = (
            '{"timestamp": "2023-01-01T10:00:00", "time": "2023-12-31T23:59:59"}'
        )
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.month == 1  # Should use timestamp, not time

    def test_invalid_timestamp_parsing(self) -> None:
        """Test handling of invalid timestamp values."""
        json_line = '{"level": "info", "timestamp": "invalid-date"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is None

    def test_z_suffix_timestamp_parsing(self) -> None:
        """Test parsing timestamps with Z suffix."""
        json_line = '{"timestamp": "2023-01-15T10:30:45.123Z"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023

    def test_no_timestamp_fields(self) -> None:
        """Test entry with no timestamp fields."""
        json_line = '{"level": "info", "message": "no timestamp here"}'
        entry = LogEntry(json_line, 1)

        assert entry.timestamp is None


class TestLogEntryLevelParsing:
    """Test level parsing functionality."""

    def test_level_field_parsing(self) -> None:
        """Test parsing level from 'level' field."""
        json_line = '{"level": "error", "message": "test"}'
        entry = LogEntry(json_line, 1)

        assert entry.level == "error"

    def test_level_field_conversion_to_string(self) -> None:
        """Test that level is converted to string."""
        json_line = '{"level": 123, "message": "test"}'
        entry = LogEntry(json_line, 1)

        assert entry.level == "123"

    def test_no_level_field(self) -> None:
        """Test entry with no level field."""
        json_line = '{"message": "no level here"}'
        entry = LogEntry(json_line, 1)

        assert entry.level is None

    def test_level_field_with_none_value(self) -> None:
        """Test level field with None value."""
        json_line = '{"level": null, "message": "test"}'
        entry = LogEntry(json_line, 1)

        assert entry.level == "None"


class TestLogEntryFromLineClassMethod:
    """Test the from_line class method."""

    def test_from_line_returns_entry_and_types(self) -> None:
        """Test that from_line returns entry and types."""
        json_line = '{"level": "info", "count": 42, "active": true}'
        entry, types = LogEntry.from_line(json_line, 10)

        assert isinstance(entry, LogEntry)
        assert entry.line_number == 10
        assert entry.is_valid_json is True

        expected_types = {"level": str, "count": int, "active": bool}
        assert types == expected_types

    def test_from_line_with_plain_text(self) -> None:
        """Test from_line with plain text."""
        plain_text = "Plain text log entry"
        entry, types = LogEntry.from_line(plain_text, 5)

        assert isinstance(entry, LogEntry)
        assert entry.line_number == 5
        assert entry.is_valid_json is False

        expected_types = {"message": str}
        assert types == expected_types

    def test_from_line_with_complex_types(self) -> None:
        """Test from_line with complex data types."""
        json_line = '{"data": {"nested": "value"}, "items": [1, 2, 3], "value": null}'
        entry, types = LogEntry.from_line(json_line, 1)

        expected_types = {"data": dict, "items": list, "value": type(None)}
        assert types == expected_types


class TestLogEntryTypesProperty:
    """Test the _types property."""

    def test_types_property_with_various_types(self) -> None:
        """Test _types property with various data types."""
        json_line = '{"str_field": "text", "int_field": 42, "float_field": 3.14, "bool_field": true, "null_field": null}'
        entry = LogEntry(json_line, 1)

        types = entry._types
        expected_types = {
            "str_field": str,
            "int_field": int,
            "float_field": float,
            "bool_field": bool,
            "null_field": type(None),
        }
        assert types == expected_types

    def test_types_property_with_complex_types(self) -> None:
        """Test _types property with complex data types."""
        json_line = '{"dict_field": {"key": "value"}, "list_field": [1, 2, 3]}'
        entry = LogEntry(json_line, 1)

        types = entry._types
        expected_types = {"dict_field": dict, "list_field": list}
        assert types == expected_types

    def test_types_property_with_plain_text(self) -> None:
        """Test _types property with plain text entry."""
        entry = LogEntry("Plain text", 1)

        types = entry._types
        expected_types = {"message": str}
        assert types == expected_types


class TestLogEntryGetValue:
    """Test the get_value method."""

    def test_get_value_line_number(self) -> None:
        """Test getting line number with # key."""
        entry = LogEntry('{"message": "test"}', 42)

        assert entry.get_value("#") == "42"

    def test_get_value_existing_field(self) -> None:
        """Test getting value of existing field."""
        json_line = '{"level": "info", "message": "test message"}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("level") == "info"
        assert entry.get_value("message") == "test message"

    def test_get_value_missing_field(self) -> None:
        """Test getting value of missing field."""
        json_line = '{"level": "info"}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("nonexistent") == ""

    def test_get_value_none_field(self) -> None:
        """Test getting value of field with None value."""
        json_line = '{"level": null}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("level") == "null"

    def test_get_value_boolean_fields(self) -> None:
        """Test getting value of boolean fields."""
        json_line = '{"active": true, "disabled": false}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("active") == "true"
        assert entry.get_value("disabled") == "false"

    def test_get_value_dict_field(self) -> None:
        """Test getting value of dict field."""
        json_line = '{"metadata": {"key": "value", "count": 42}}'
        entry = LogEntry(json_line, 1)

        result = entry.get_value("metadata")
        # Should be JSON string
        parsed = json.loads(result)
        assert parsed == {"key": "value", "count": 42}

    def test_get_value_list_field(self) -> None:
        """Test getting value of list field."""
        json_line = '{"items": [1, 2, 3, "four"]}'
        entry = LogEntry(json_line, 1)

        result = entry.get_value("items")
        # Should be JSON string
        parsed = json.loads(result)
        assert parsed == [1, 2, 3, "four"]

    def test_get_value_numeric_fields(self) -> None:
        """Test getting value of numeric fields."""
        json_line = '{"count": 42, "price": 19.99}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("count") == "42"
        assert entry.get_value("price") == "19.99"

    def test_get_value_unicode_handling(self) -> None:
        """Test getting value with unicode characters."""
        json_line = '{"message": "Hello 世界", "emoji": "🚀"}'
        entry = LogEntry(json_line, 1)

        assert entry.get_value("message") == "Hello 世界"
        assert entry.get_value("emoji") == "🚀"


class TestLogEntryGetSortableValue:
    """Test the get_sortable_value method."""

    def test_get_sortable_value_line_number(self) -> None:
        """Test getting sortable value for line number."""
        entry = LogEntry('{"message": "test"}', 42)

        result = entry.get_sortable_value("#", int)
        assert result == 42

    def test_get_sortable_value_timestamp_field(self) -> None:
        """Test getting sortable value for timestamp field."""
        json_line = '{"timestamp": "2023-01-15T10:30:45"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("timestamp", datetime)
        assert isinstance(result, datetime)
        assert result.year == 2023

    def test_get_sortable_value_timestamp_field_no_timestamp(self) -> None:
        """Test getting sortable value for timestamp field when no timestamp parsed."""
        json_line = '{"message": "no timestamp"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("timestamp", datetime)
        assert result == ""

    def test_get_sortable_value_none_type(self) -> None:
        """Test getting sortable value for NoneType."""
        json_line = '{"value": null}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("value", NoneType)
        assert result == "null"

    def test_get_sortable_value_missing_field_int(self) -> None:
        """Test getting sortable value for missing field with int type."""
        json_line = '{"message": "test"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("missing_int", int)
        assert result == -math.inf

    def test_get_sortable_value_missing_field_float(self) -> None:
        """Test getting sortable value for missing field with float type."""
        json_line = '{"message": "test"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("missing_float", float)
        assert result == -math.inf

    def test_get_sortable_value_missing_field_string(self) -> None:
        """Test getting sortable value for missing field with string type."""
        json_line = '{"message": "test"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("missing_string", str)
        assert result == ""

    def test_get_sortable_value_int_field(self) -> None:
        """Test getting sortable value for int field."""
        json_line = '{"count": 42}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("count", int)
        assert result == 42

    def test_get_sortable_value_float_field(self) -> None:
        """Test getting sortable value for float field."""
        json_line = '{"price": 19.99}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("price", float)
        assert result == 19.99

    def test_get_sortable_value_string_field(self) -> None:
        """Test getting sortable value for string field."""
        json_line = '{"level": "info"}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("level", str)
        assert result == "info"

    def test_get_sortable_value_complex_field_as_string(self) -> None:
        """Test getting sortable value for complex field converted to string."""
        json_line = '{"data": {"key": "value"}}'
        entry = LogEntry(json_line, 1)

        result = entry.get_sortable_value("data", str)
        assert result == "{'key': 'value'}"


class TestLogEntryMatchesFilter:
    """Test the matches_filter method."""

    def test_matches_filter_single_match(self) -> None:
        """Test matching a single filter."""
        json_line = '{"level": "error", "message": "database connection failed"}'
        entry = LogEntry(json_line, 1)

        filters = {"level": "error"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_single_no_match(self) -> None:
        """Test not matching a single filter."""
        json_line = '{"level": "info", "message": "operation successful"}'
        entry = LogEntry(json_line, 1)

        filters = {"level": "error"}
        assert entry.matches_filter(filters) is False

    def test_matches_filter_multiple_match(self) -> None:
        """Test matching multiple filters."""
        json_line = (
            '{"level": "error", "service": "database", "message": "connection failed"}'
        )
        entry = LogEntry(json_line, 1)

        filters = {"level": "error", "service": "database"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_multiple_partial_match(self) -> None:
        """Test partial matching of multiple filters."""
        json_line = (
            '{"level": "error", "service": "api", "message": "connection failed"}'
        )
        entry = LogEntry(json_line, 1)

        filters = {"level": "error", "service": "database"}
        assert entry.matches_filter(filters) is False

    def test_matches_filter_case_insensitive(self) -> None:
        """Test that filter matching is case insensitive."""
        json_line = '{"level": "ERROR", "message": "Database Connection Failed"}'
        entry = LogEntry(json_line, 1)

        filters = {"level": "error", "message": "database"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_partial_string_match(self) -> None:
        """Test that filters match partial strings."""
        json_line = '{"message": "user authentication failed for john.doe@example.com"}'
        entry = LogEntry(json_line, 1)

        filters = {"message": "authentication"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_empty_filter_value(self) -> None:
        """Test that empty filter values are ignored."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        filters = {"level": "", "message": "test"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_empty_filters(self) -> None:
        """Test that empty filters dict matches everything."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        filters = {}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_nonexistent_field(self) -> None:
        """Test filtering on nonexistent field."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        filters = {"nonexistent": "value"}
        assert entry.matches_filter(filters) is False

    def test_matches_filter_line_number(self) -> None:
        """Test filtering on line number field."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 42)

        filters = {"#": "42"}
        assert entry.matches_filter(filters) is True

    def test_matches_filter_complex_field(self) -> None:
        """Test filtering on complex field (dict/list)."""
        json_line = '{"metadata": {"user": "john", "action": "login"}}'
        entry = LogEntry(json_line, 1)

        filters = {"metadata": "john"}
        assert entry.matches_filter(filters) is True


class TestLogEntryMatchesSearch:
    """Test the matches_search method."""

    def test_matches_search_empty_term(self) -> None:
        """Test that empty search term matches everything."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("") is True
        assert entry.matches_search(None) is True

    def test_matches_search_in_data_values(self) -> None:
        """Test searching in data values."""
        json_line = '{"level": "error", "message": "database connection failed", "service": "api"}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("database") is True
        assert entry.matches_search("error") is True
        assert entry.matches_search("api") is True

    def test_matches_search_case_insensitive(self) -> None:
        """Test that search is case insensitive."""
        json_line = '{"level": "ERROR", "message": "Database Connection Failed"}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("error") is True
        assert entry.matches_search("database") is True
        assert entry.matches_search("CONNECTION") is True

    def test_matches_search_in_raw_line(self) -> None:
        """Test searching in raw line when not found in data values."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        # Search for something that's in the raw JSON but not as a separate value
        assert entry.matches_search("level") is True
        assert entry.matches_search("{") is True

    def test_matches_search_no_match(self) -> None:
        """Test search with no matches."""
        json_line = '{"level": "info", "message": "test"}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("nonexistent") is False
        assert entry.matches_search("xyz") is False

    def test_matches_search_plain_text_entry(self) -> None:
        """Test searching in plain text entry."""
        plain_text = "This is a plain text log entry with important information"
        entry = LogEntry(plain_text, 1)

        assert entry.matches_search("plain") is True
        assert entry.matches_search("important") is True
        assert entry.matches_search("nonexistent") is False

    def test_matches_search_numeric_values(self) -> None:
        """Test searching in numeric values."""
        json_line = '{"count": 42, "price": 19.99, "active": true}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("42") is True
        assert entry.matches_search("19.99") is True
        assert entry.matches_search("true") is True

    def test_matches_search_complex_values(self) -> None:
        """Test searching in complex values (dict/list)."""
        json_line = '{"metadata": {"user": "john", "roles": ["admin", "user"]}, "tags": ["important", "urgent"]}'
        entry = LogEntry(json_line, 1)

        assert entry.matches_search("john") is True
        assert entry.matches_search("admin") is True
        assert entry.matches_search("important") is True


class TestLogEntryEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_large_json(self) -> None:
        """Test handling of very large JSON objects."""
        large_data = {"field_" + str(i): f"value_{i}" for i in range(1000)}
        json_line = json.dumps(large_data)
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert len(entry.data) == 1000
        assert entry.get_value("field_500") == "value_500"

    def test_deeply_nested_json(self) -> None:
        """Test handling of deeply nested JSON."""
        nested_data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
        json_line = json.dumps(nested_data)
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        result = entry.get_value("level1")
        parsed = json.loads(result)
        assert parsed["level2"]["level3"]["level4"]["value"] == "deep"

    def test_json_with_special_characters(self) -> None:
        """Test JSON with special characters and escape sequences."""
        json_line = r'{"message": "Line 1\nLine 2\tTabbed", "quote": "He said \"Hello\"", "backslash": "C:\\path"}'
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert "Line 1\nLine 2\tTabbed" in entry.get_value("message")
        assert 'He said "Hello"' in entry.get_value("quote")

    def test_json_with_unicode_escape_sequences(self) -> None:
        """Test JSON with unicode escape sequences."""
        json_line = '{"unicode": "\\u0048\\u0065\\u006c\\u006c\\u006f", "emoji": "\\ud83d\\ude80"}'
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert entry.get_value("unicode") == "Hello"

    def test_empty_json_object(self) -> None:
        """Test empty JSON object."""
        json_line = "{}"
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert entry.data == {}
        assert entry.level is None
        assert entry.timestamp is None

    def test_json_with_null_values(self) -> None:
        """Test JSON with various null values."""
        json_line = (
            '{"null_field": null, "empty_string": "", "zero": 0, "false_bool": false}'
        )
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert entry.get_value("null_field") == "null"
        assert entry.get_value("empty_string") == ""
        assert entry.get_value("zero") == "0"
        assert entry.get_value("false_bool") == "false"

    def test_json_with_extreme_numbers(self) -> None:
        """Test JSON with extreme numeric values."""
        json_line = '{"big_int": 9223372036854775807, "small_int": -9223372036854775808, "big_float": 1.7976931348623157e+308, "small_float": 2.2250738585072014e-308}'
        entry = LogEntry(json_line, 1)

        assert entry.is_valid_json is True
        assert entry.get_sortable_value("big_int", int) == 9223372036854775807
        assert entry.get_sortable_value("small_int", int) == -9223372036854775808

    def test_line_number_edge_cases(self) -> None:
        """Test edge cases with line numbers."""
        # Test with line number 0
        entry1 = LogEntry('{"message": "test"}', 0)
        assert entry1.line_number == 0
        assert entry1.get_value("#") == "0"

        # Test with very large line number
        entry2 = LogEntry('{"message": "test"}', 999999999)
        assert entry2.line_number == 999999999
        assert entry2.get_value("#") == "999999999"

    def test_malformed_json_variations(self) -> None:
        """Test various types of malformed JSON."""
        # These are truly malformed JSON that should fail parsing
        malformed_cases = [
            '{"incomplete": ',
            '{"missing_quote: "value"}',
            "{invalid_json_structure}",
        ]

        for malformed_json in malformed_cases:
            entry = LogEntry(malformed_json, 1)
            assert entry.is_valid_json is False
            # Note: raw_line is stripped, so we compare with the stripped version
            assert entry.data == {"message": malformed_json.strip()}

    def test_valid_json_but_not_dict(self) -> None:
        """Test valid JSON that's not a dictionary."""
        non_dict_cases = [
            "null",  # Valid JSON but not a dict
            "[]",  # Valid JSON but not a dict
            '"string"',  # Valid JSON but not a dict
            "123",  # Valid JSON but not a dict
            "true",  # Valid JSON but not a dict
        ]

        for json_case in non_dict_cases:
            entry = LogEntry(json_case, 1)
            assert entry.is_valid_json is False
            assert entry.data == {"message": json_case.strip()}

    def test_edge_case_valid_json(self) -> None:
        """Test edge cases that are actually valid JSON."""
        # These might look malformed but are actually valid
        edge_cases = [
            (
                '{"duplicate": "key", "duplicate": "key2"}',
                {"duplicate": "key2"},
            ),  # Duplicate keys - second wins
            (
                '{"trailing_comma": "value"}',
                {"trailing_comma": "value"},
            ),  # No trailing comma here, actually valid
        ]

        for json_str, expected_data in edge_cases:
            entry = LogEntry(json_str, 1)
            assert entry.is_valid_json is True
            assert entry.data == expected_data


class TestLogEntryIntegration:
    """Integration tests combining multiple features."""

    def test_complete_log_entry_processing(self) -> None:
        """Test complete processing of a realistic log entry."""
        json_line = '{"timestamp": "2023-01-15T10:30:45.123", "level": "error", "service": "user-auth", "message": "Failed login attempt", "user_id": 12345, "ip_address": "192.168.1.100", "metadata": {"attempt_count": 3, "locked": true}}'
        entry = LogEntry(json_line, 42)

        # Test basic properties
        assert entry.line_number == 42
        assert entry.is_valid_json is True
        assert entry.level == "error"
        assert entry.timestamp is not None
        assert entry.timestamp.year == 2023

        # Test get_value for various field types
        assert entry.get_value("#") == "42"
        assert entry.get_value("level") == "error"
        assert entry.get_value("service") == "user-auth"
        assert entry.get_value("user_id") == "12345"
        assert entry.get_value("ip_address") == "192.168.1.100"

        # Test complex field
        metadata_json = entry.get_value("metadata")
        metadata = json.loads(metadata_json)
        assert metadata["attempt_count"] == 3
        assert metadata["locked"] is True

        # Test filtering
        assert entry.matches_filter({"level": "error"}) is True
        assert entry.matches_filter({"service": "user-auth"}) is True
        assert entry.matches_filter({"level": "info"}) is False
        assert entry.matches_filter({"level": "error", "service": "user-auth"}) is True

        # Test searching
        assert entry.matches_search("failed") is True
        assert entry.matches_search("login") is True
        assert entry.matches_search("12345") is True
        assert entry.matches_search("192.168") is True
        assert entry.matches_search("nonexistent") is False

        # Test sortable values
        assert entry.get_sortable_value("user_id", int) == 12345
        assert entry.get_sortable_value("level", str) == "error"
        assert isinstance(entry.get_sortable_value("timestamp", datetime), datetime)

    def test_plain_text_log_processing(self) -> None:
        """Test processing of plain text log entries."""
        plain_text = "2023-01-15 10:30:45 ERROR [user-auth] Failed login attempt for user 12345 from 192.168.1.100"
        entry = LogEntry(plain_text, 100)

        # Test basic properties
        assert entry.line_number == 100
        assert entry.is_valid_json is False
        assert entry.level is None
        assert entry.timestamp is None
        assert entry.data == {"message": plain_text}

        # Test get_value
        assert entry.get_value("#") == "100"
        assert entry.get_value("message") == plain_text
        assert entry.get_value("nonexistent") == ""

        # Test filtering
        assert entry.matches_filter({"message": "ERROR"}) is True
        assert entry.matches_filter({"message": "user-auth"}) is True
        assert entry.matches_filter({"message": "INFO"}) is False

        # Test searching
        assert entry.matches_search("ERROR") is True
        assert entry.matches_search("12345") is True
        assert entry.matches_search("failed") is True
        assert entry.matches_search("nonexistent") is False

    def test_timestamp_parsing_edge_cases(self) -> None:
        """Test timestamp parsing with various edge cases."""
        # Test with multiple timestamp fields - should use first valid one
        json_line = '{"timestamp": "invalid", "time": "2023-05-15T14:30:00", "@timestamp": "2023-01-01T00:00:00"}'
        entry = LogEntry(json_line, 1)

        # Should use "time" field since "timestamp" is invalid
        assert entry.timestamp is not None
        assert entry.timestamp.month == 5  # From "time" field, not "@timestamp"

        # Test with all invalid timestamp fields
        json_line2 = '{"timestamp": "invalid", "time": "also-invalid", "@timestamp": "not-a-date"}'
        entry2 = LogEntry(json_line2, 1)

        assert entry2.timestamp is None

    def test_types_consistency_with_from_line(self) -> None:
        """Test that _types property is consistent with from_line method."""
        json_line = '{"str": "text", "int": 42, "float": 3.14, "bool": true, "null": null, "dict": {"key": "value"}, "list": [1, 2, 3]}'

        entry, types_from_method = LogEntry.from_line(json_line, 1)
        types_from_property = entry._types

        assert types_from_method == types_from_property

        expected_types = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "null": type(None),
            "dict": dict,
            "list": list,
        }
        assert types_from_property == expected_types
