"""Column model for table display."""

import dataclasses


@dataclasses.dataclass
class Column:
    """Represents a column in the table"""

    name: str
    width: int = 0
