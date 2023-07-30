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
