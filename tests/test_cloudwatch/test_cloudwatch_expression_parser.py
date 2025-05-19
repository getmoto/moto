import datetime

from moto.cloudwatch.metric_data_expression_parser import parse_expression


def test_simple_expression():
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "vals": [25.0],
            "timestamps": ["timestamp1"],
        }
    ]
    res = parse_expression("totalBytes", result_from_previous_queries)
    assert res == ([25.0], ["timestamp1"])


def test_missing_expression():
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "vals": [25.0],
            "timestamps": ["timestamp1"],
        }
    ]
    res = parse_expression("unknown", result_from_previous_queries)
    assert res == ([], [])


def test_complex_expression():
    result_from_previous_queries = [
        {
            "id": "totalBytes",
            "label": "metric Sum",
            "vals": [25.0],
            "timestamps": ["timestamp1"],
        }
    ]
    res = parse_expression("totalBytes/10", result_from_previous_queries)
    assert res == ([], [])


def test_addition_expression():
    t3 = datetime.datetime.now(datetime.timezone.utc)
    t2 = t3 - datetime.timedelta(minutes=1)
    t1 = t2 - datetime.timedelta(minutes=1)

    results_from_previous_queries = [
        {
            "id": "first",
            "label": "first",
            "vals": [10.0, 15.0, 30.0],
            "timestamps": [t1, t2, t3],
        },
        {
            "id": "second",
            "label": "second",
            "vals": [25.0, 5.0, 3.0],
            "timestamps": [t1, t2, t3],
        },
    ]
    res = parse_expression("first + second", results_from_previous_queries)
    assert res == ([35.0, 20.0, 33.0], [t1, t2, t3])
