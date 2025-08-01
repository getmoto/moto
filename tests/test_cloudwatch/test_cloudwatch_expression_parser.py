from moto.cloudwatch.metric_data_expression_parser import parse_expression
from moto.core.utils import utcnow


def test_simple_expression():
    timestamp = utcnow()
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "values": [25.0],
            "timestamps": [timestamp],
        }
    ]
    res = parse_expression("totalBytes", result_from_previous_queries)
    assert res == ([25.0], [timestamp])


def test_missing_expression():
    timestamp = utcnow()
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "values": [25.0],
            "timestamps": [timestamp],
        }
    ]
    res = parse_expression("unknown", result_from_previous_queries)
    assert res == ([], [])


def test_complex_expression():
    timestamp = utcnow()
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "values": [25.0],
            "timestamps": [timestamp],
        }
    ]
    res = parse_expression("totalBytes/10", result_from_previous_queries)
    assert res == ([], [])
