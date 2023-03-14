import re
from typing import Any, Callable

boto_response = dict[str, Any]
boto_factory = Callable[[int], list[boto_response]]


class MatchingRegex:
    """Assert that a given string meets some expectations."""

    def __init__(self, pattern: str):
        self._regex = re.compile(pattern)

    def __eq__(self, value):
        """Match value against stored pattern."""
        return bool(self._regex.match(value))

    def __repr__(self):
        """Output nice representation."""
        return self._regex.pattern
