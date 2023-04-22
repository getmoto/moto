from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import FakeSecret


def name_filter(secret: "FakeSecret", names: List[str]) -> bool:
    return _matcher(names, [secret.name])


def description_filter(secret: "FakeSecret", descriptions: List[str]) -> bool:
    return _matcher(descriptions, [secret.description])  # type: ignore


def tag_key(secret: "FakeSecret", tag_keys: List[str]) -> bool:
    return _matcher(tag_keys, [tag["Key"] for tag in secret.tags])


def tag_value(secret: "FakeSecret", tag_values: List[str]) -> bool:
    return _matcher(tag_values, [tag["Value"] for tag in secret.tags])


def filter_all(secret: "FakeSecret", values: List[str]) -> bool:
    attributes = (
        [secret.name, secret.description]
        + [tag["Key"] for tag in secret.tags]
        + [tag["Value"] for tag in secret.tags]
    )

    return _matcher(values, attributes)  # type: ignore


def _matcher(patterns: List[str], strings: List[str]) -> bool:
    for pattern in [p for p in patterns if p.startswith("!")]:
        for string in strings:
            if _match_pattern(pattern[1:], string):
                return False

    for pattern in [p for p in patterns if not p.startswith("!")]:
        for string in strings:
            if _match_pattern(pattern, string):
                return True
    return False


def _match_pattern(pattern: str, value: str) -> bool:
    for word in pattern.split(" "):
        if word not in value:
            return False
    return True
