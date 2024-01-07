import boto3
import requests

from moto import mock_aws, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_execute_statement():
    rdsdata = boto3.client("rds-data", region_name="eu-west-1")

    resp = rdsdata.execute_statement(
        resourceArn="not applicable",
        secretArn="not applicable",
        sql="SELECT some FROM thing",
    )

    assert resp["records"] == []


@mock_aws
def test_set_query_results():
    base_url = (
        settings.test_server_mode_endpoint()
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )

    sql_result = {
        "results": [
            {
                "records": [[{"isNull": True}], [{"isNull": False}]],
                "columnMetadata": [{"name": "a"}],
                "formattedRecords": "some json",
            }
        ],
        "region": "us-west-1",
    }
    resp = requests.post(
        f"{base_url}/moto-api/static/rds-data/statement-results",
        json=sql_result,
    )
    assert resp.status_code == 201

    rdsdata = boto3.client("rds-data", region_name="us-west-1")

    resp = rdsdata.execute_statement(
        resourceArn="not applicable",
        secretArn="not applicable",
        sql="SELECT some FROM thing",
    )

    assert resp["records"] == [[{"isNull": True}], [{"isNull": False}]]
    assert resp["formattedRecords"] == "some json"
