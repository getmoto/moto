import boto3
import requests

from moto import mock_aws, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_get_cost_and_usage():
    ce = boto3.client("ce", region_name="eu-west-1")

    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": "2024-01-01", "End": "2024-02-01"},
        Granularity="DAILY",
        Metrics=["UNBLENDEDCOST"],
    )

    assert resp["DimensionValueAttributes"] == []
    assert resp["ResultsByTime"] == []


@mock_aws
def test_set_query_results():
    base_url = (
        settings.test_server_mode_endpoint()
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )

    cost_and_usage_result = {
        "results": [
            {
                "ResultsByTime": [
                    {
                        "TimePeriod": {"Start": "2024-01-01", "End": "2024-01-02"},
                        "Total": {
                            "BlendedCost": {"Amount": "0.0101516483", "Unit": "USD"}
                        },
                        "Groups": [],
                        "Estimated": False,
                    }
                ],
                "DimensionValueAttributes": [{"Value": "v", "Attributes": {"a": "b"}}],
            }
        ],
    }
    resp = requests.post(
        f"{base_url}/moto-api/static/ce/cost-and-usage-results",
        json=cost_and_usage_result,
    )
    assert resp.status_code == 201

    ce = boto3.client("ce", region_name="us-west-1")

    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": "2024-01-01", "End": "2024-02-01"},
        Granularity="DAILY",
        Metrics=["BLENDEDCOST", "AMORTIZEDCOST"],
    )

    resp.pop("ResponseMetadata")
    assert resp == cost_and_usage_result["results"][0]
