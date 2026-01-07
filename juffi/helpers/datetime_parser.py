"""Datetime parsing utilities."""

from datetime import datetime


def try_parse_datetime(ts_str: str) -> datetime | None:
    """Try to parse a datetime string using common formats."""
    no_z_ts_str = ts_str.replace("Z", "")
    for fmt in [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]:
        try:
            return datetime.strptime(no_z_ts_str, fmt)
        except ValueError:
            pass

    return None
