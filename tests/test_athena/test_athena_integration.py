import json
from unittest import SkipTest
from uuid import uuid4

import boto3
import pytest
import requests

from moto import settings
from tests.test_athena import athena_aws_verified

DATA = ""
DATA += json.dumps({"k1": "r1_v1", "k2": "r1_v2", "k3": 1}) + "\n"
DATA += json.dumps({"k1": "r2_v1", "k2": "r2_v2", "k3": 2}) + "\n"
DATA += json.dumps({"k1": "r3_v1", "k2": "r3_v2"})

ROWS_DATA = [
    {"Data": [{"VarCharValue": "k1"}, {"VarCharValue": "k2"}, {"VarCharValue": "k3"}]},
    {
        "Data": [
            {"VarCharValue": "r1_v1"},
            {"VarCharValue": "r1_v2"},
            {"VarCharValue": "1"},
        ]
    },
    {
        "Data": [
            {"VarCharValue": "r2_v1"},
            {"VarCharValue": "r2_v2"},
            {"VarCharValue": "2"},
        ]
    },
    {"Data": [{"VarCharValue": "r3_v1"}, {"VarCharValue": "r3_v2"}, {}]},
]
COLUMN_INFO = [
    {
        "CatalogName": "hive",
        "SchemaName": "",
        "TableName": "",
        "Name": "k1",
        "Label": "k1",
        "Type": "varchar",
        "Precision": 2147483647,
        "Scale": 0,
        "Nullable": "UNKNOWN",
        "CaseSensitive": True,
    },
    {
        "CatalogName": "hive",
        "SchemaName": "",
        "TableName": "",
        "Name": "k2",
        "Label": "k2",
        "Type": "varchar",
        "Precision": 2147483647,
        "Scale": 0,
        "Nullable": "UNKNOWN",
        "CaseSensitive": True,
    },
    {
        "CatalogName": "hive",
        "SchemaName": "",
        "TableName": "",
        "Name": "k3",
        "Label": "k3",
        "Type": "integer",
        "Precision": 10,
        "Scale": 0,
        "Nullable": "UNKNOWN",
        "CaseSensitive": False,
    },
]


@athena_aws_verified
@pytest.mark.aws_verified
def test_athena_csv_result(bucket_name=None, is_aws: bool = False):
    if not settings.TEST_DECORATOR_MODE:
        raise SkipTest("No point in testing this outside of decorators")

    s3 = boto3.client("s3", "us-east-1")
    s3.put_object(Bucket=bucket_name, Key="input/data1.json", Body=DATA.encode("utf-8"))

    athena = boto3.client("athena", "us-east-1")

    config = {"OutputLocation": f"s3://{bucket_name}/output/"}
    db_name = f"db_{str(uuid4())[0:6]}"

    athena.start_query_execution(
        QueryString=f"create database {db_name}", ResultConfiguration=config
    )

    context = {"Database": db_name}
    CREATE_TABLE = f"""CREATE EXTERNAL TABLE mytable (
k1 string,
k2 string,
k3 int
) 
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.IgnoreKeyTextOutputFormat'
LOCATION 's3://{bucket_name}/input/'; """
    get_query_results(CREATE_TABLE, athena, config, context)

    if not is_aws:
        athena_result = {
            "results": [
                {
                    "rows": ROWS_DATA,
                    "column_info": COLUMN_INFO,
                }
            ]
        }
        requests.post(
            "http://motoapi.amazonaws.com/moto-api/static/athena/query-results",
            json=athena_result,
        )

    query_exec_id, resp = get_query_results(
        "SELECT * FROM mytable", athena, config, context
    )
    assert resp["ResultSet"] == {
        "Rows": ROWS_DATA,
        "ResultSetMetadata": {"ColumnInfo": COLUMN_INFO},
    }

    file = s3.get_object(Bucket=bucket_name, Key=f"output/{query_exec_id}.csv")
    assert (
        file["Body"].read()
        == b'"k1","k2","k3"\n"r1_v1","r1_v2","1"\n"r2_v1","r2_v2","2"\n"r3_v1","r3_v2",\n'
    )

    get_query_results("DROP TABLE mytable", athena, config, context)

    get_query_results(f"DROP database {db_name}", athena, config, context)


def get_query_results(CREATE_TABLE, athena, config, context):
    resp = athena.start_query_execution(
        QueryString=CREATE_TABLE,
        QueryExecutionContext=context,
        ResultConfiguration=config,
    )
    query_execution_id = resp["QueryExecutionId"]

    status = ""
    while status not in ["SUCCEEDED", "FAILED"]:
        resp = athena.get_query_execution(QueryExecutionId=query_execution_id)[
            "QueryExecution"
        ]

        status = resp["Status"]["State"]

    resp = athena.get_query_results(QueryExecutionId=query_execution_id)
    return query_execution_id, resp
