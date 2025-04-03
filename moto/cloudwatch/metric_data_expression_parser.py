from typing import Any, Dict, List, SupportsFloat, Tuple

from .exceptions import ValidationError


def parse_expression(
    expression: str, results: List[Dict[str, Any]]
) -> Tuple[List[SupportsFloat], List[str]]:
    values: List[SupportsFloat] = []
    timestamps: List[str] = []

    if "+" in expression:
        expression = expression.replace(" ", "")
        plus_splits = expression.split("+")
        if len(plus_splits) != 2:
            raise ValidationError(
                "Metric math expressions only support adding two values together"
            )

        by_timestamp = results_by_timestamp(results)
        for timestamp, vals in by_timestamp.items():
            first = vals.get(plus_splits[0], 0.0)
            second = vals.get(plus_splits[1], 0.0)

            values.append(first + second)
            timestamps.append(timestamp)

    for result in results:
        if result.get("id") == expression:
            values.extend(result["vals"])
            timestamps.extend(result["timestamps"])
    return values, timestamps


def results_by_timestamp(
    results: List[Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}

    for result in results:
        this_id = result.get("id")
        if not this_id:
            continue

        for i in range(0, len(result["vals"])):
            timestamp = result["timestamps"][i]
            value = result["vals"][i]

            if timestamp not in out:
                out[timestamp] = {}

            out[timestamp][this_id] = value

    return out
