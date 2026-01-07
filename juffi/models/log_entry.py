"""Module for representing a single log entry"""

import json
import math
from datetime import datetime
from types import NoneType
from typing import Any, Type, TypeVar

from juffi.helpers.datetime_parser import try_parse_datetime

MISSING = object()
T = TypeVar("T")


class LogEntry:
    """Represents a single log entry"""

    def __init__(self, raw_line: str, line_number: int) -> None:
        self.raw_line: str = raw_line.strip()
        self.line_number: int = line_number
        self.data: dict[str, Any] = {}
        self.timestamp: datetime | None = None
        self.level: str | None = None
        self.is_valid_json: bool = False

        try:
            data = json.loads(self.raw_line)
            if not isinstance(data, dict):
                raise ValueError("Not a dictionary")

            self.data = data
            self.is_valid_json = True
        except ValueError:
            self.data = {"message": self.raw_line}

        for ts_field in [
            "timestamp",
            "time",
            "@timestamp",
            "datetime",
            "date",
        ]:
            if ts_field in self.data:
                ts_str = str(self.data[ts_field])
                timestamp = try_parse_datetime(ts_str)
                if timestamp:
                    self.timestamp = timestamp
                    break

        if "level" in self.data:
            self.level = str(self.data["level"])

    @classmethod
    def from_line(
        cls, line: str, line_number: int
    ) -> tuple["LogEntry", dict[str, type]]:
        """Create a LogEntry from a line of text and return the types of its fields"""
        entry = LogEntry(line, line_number)
        return entry, entry.types

    @property
    def types(self) -> dict[str, type]:
        """Get the types of all fields in the entry data"""
        types = {}
        for key, value in self.data.items():
            types[key] = type(value)
        return types

    def get_value(self, key: str) -> str:
        """Get the value of a field, formatted as a string"""
        if key == "#":
            value = self.line_number
        else:
            value = self.data.get(key, MISSING)

        if value is MISSING:
            return ""
        if value is None:
            return "null"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def get_sortable_value(self, key: str, type_: Type[T]) -> T:
        """Get the value of a field, formatted for sorting"""
        blank = {
            int: -math.inf,
            float: -math.inf,
        }
        value = self.data.get(key, MISSING)
        result: Any
        if key == "#":
            result = self.line_number

        elif key == "timestamp":
            if self.timestamp:
                result = self.timestamp
            else:
                result = ""
        elif type_ == NoneType:
            result = "null"

        elif value is MISSING:
            result = blank.get(type_, "")

        elif type_ in (int, float):
            result = value
        else:
            result = str(value)
        return result

    def matches_filter(self, filters: dict[str, str]) -> bool:
        """Check if the entry matches all the given filters"""
        for key, filter_value in filters.items():
            if not filter_value:
                continue
            entry_value = self.get_value(key).lower()
            if filter_value.lower() not in entry_value:
                return False
        return True

    def matches_search(self, search_term: str) -> bool:
        """Check if the entry matches the search term"""
        if not search_term:
            return True
        search_lower = search_term.lower()

        for value in self.data.values():
            if search_lower in str(value).lower():
                return True

        return search_lower in self.raw_line.lower()
