import boto3
import requests

from moto import mock_rdsdata, settings

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_rdsdata
def test_execute_statement():
    rdsdata = boto3.client("rds-data", region_name="eu-west-1")

    resp = rdsdata.execute_statement(
        resourceArn="not applicable",
        secretArn="not applicable",
        sql="SELECT some FROM thing",
    )

    assert resp["records"] == []


@mock_rdsdata
def test_set_query_results():
    base_url = (
        "localhost:5000" if settings.TEST_SERVER_MODE else "motoapi.amazonaws.com"
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
        f"http://{base_url}/moto-api/static/rds-data/statement-results",
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
