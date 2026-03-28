# import json
import string
from typing import Any, Optional

from moto.moto_api._internal import mock_random as random


def random_id(size: int = 13) -> str:
    chars = list(range(10)) + list(string.ascii_lowercase)
    return "".join(str(random.choice(chars)) for x in range(size))


def random_cluster_id() -> str:
    return random_id(size=25)


def random_job_id() -> str:
    return random_id(size=19)


def paginated_list(
    full_list: list[Any], sort_key: str, max_results: int, next_token: Optional[str]
) -> tuple[list[Any], Optional[str]]:
    """
    Returns a tuple containing a slice of the full list starting at next_token and ending with at most the max_results
    number of elements, and the new next_token which can be passed back in for the next segment of the full list.
    """
    if next_token is None or not next_token:
        next_token = 0  # type: ignore
    next_token = int(next_token)  # type: ignore

    sorted_list = sorted(full_list, key=lambda d: d[sort_key])

    end_index = next_token + max_results  # type: ignore
    values = sorted_list[next_token:end_index]  # type: ignore
    if end_index < len(sorted_list):
        new_next_token = str(end_index)
    else:
        new_next_token = None
    return values, new_next_token
