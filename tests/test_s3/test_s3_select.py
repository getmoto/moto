import boto3
import json
import pytest

from . import s3_aws_verified


SIMPLE_JSON = {"a1": "b1", "a2": "b2", "a3": None}
SIMPLE_JSON2 = {"a1": "b2", "a3": "b3"}
NESTED_JSON = {"a1": {"b1": "b2"}, "a2": [True, False], "a3": True, "a4": [1, 5]}
EXTENSIVE_JSON = [
    {
        "staff": [
            {
                "name": "Janelyn M",
                "city": "Chicago",
                "kids": [{"Name": "Josh"}, {"Name": "Jay"}],
            },
            {"name": "Stacy P", "city": "Seattle", "kids": {"Name": "Josh"}},
        ],
        "country": "USA",
    }
]
SIMPLE_LIST = [SIMPLE_JSON, SIMPLE_JSON2]
SIMPLE_CSV = """a,b,c
e,r,f
y,u,i
q,w,y"""


def create_test_files(bucket_name):
    client = boto3.client("s3", "us-east-1")
    client.put_object(
        Bucket=bucket_name, Key="simple.json", Body=json.dumps(SIMPLE_JSON)
    )
    client.put_object(Bucket=bucket_name, Key="list.json", Body=json.dumps(SIMPLE_LIST))
    client.put_object(Bucket=bucket_name, Key="simple_csv", Body=SIMPLE_CSV)
    client.put_object(
        Bucket=bucket_name,
        Key="extensive.json",
        Body=json.dumps(EXTENSIVE_JSON),
    )
    client.put_object(
        Bucket=bucket_name,
        Key="nested.json",
        Body=json.dumps(NESTED_JSON),
    )


@pytest.mark.aws_verified
@s3_aws_verified
def test_query_all(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="simple.json",
        Expression="SELECT * FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"a1":"b1","a2":"b2","a3":null},'}} in result

    # Verify result is valid JSON
    json.loads(result[0]["Records"]["Payload"][0:-1].decode("utf-8"))

    # Verify result contains metadata
    stats = [res for res in result if "Stats" in res][0]["Stats"]
    assert "BytesScanned" in stats["Details"]
    assert "BytesProcessed" in stats["Details"]
    assert "BytesReturned" in stats["Details"]
    assert {"End": {}} in result


@pytest.mark.aws_verified
@s3_aws_verified
def test_count_function(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="simple.json",
        Expression="SELECT count(*) FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"_1":1},'}} in result


@pytest.mark.aws_verified
@s3_aws_verified
@pytest.mark.xfail(message="Not yet implement in our parser")
def test_count_as(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="simple.json",
        Expression="SELECT count(*) as cnt FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"cnt":1},'}} in result


@pytest.mark.aws_verified
@s3_aws_verified
@pytest.mark.xfail(message="Not yet implement in our parser")
def test_count_list_as(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="list.json",
        Expression="SELECT count(*) as cnt FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"cnt":1},'}} in result


@pytest.mark.aws_verified
@s3_aws_verified
def test_count_csv(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="simple_csv",
        Expression="SELECT count(*) FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"CSV": {"FileHeaderInfo": "USE", "FieldDelimiter": ","}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"_1":3},'}} in result


@pytest.mark.aws_verified
@s3_aws_verified
def test_default_record_delimiter(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="simple_csv",
        Expression="SELECT count(*) FROM S3Object",
        ExpressionType="SQL",
        InputSerialization={"CSV": {"FileHeaderInfo": "USE", "FieldDelimiter": ","}},
        # RecordDelimiter is not specified - should default to new line (\n)
        OutputSerialization={"JSON": {}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b'{"_1":3}\n'}} in result


@pytest.mark.aws_verified
@s3_aws_verified
def test_extensive_json__select_list(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="extensive.json",
        Expression="select * from s3object[*].staff[*] s",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    assert {"Records": {"Payload": b"{},"}} in result


@pytest.mark.aws_verified
@s3_aws_verified
def test_extensive_json__select_all(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="extensive.json",
        Expression="select * from s3object s",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    records = [res for res in result if "Records" in res][0]["Records"][
        "Payload"
    ].decode("utf-8")

    # For some reason, AWS returns records with a comma at the end
    assert records[-1] == ","

    # Because the original doc is a list, it is returned like this
    assert json.loads(records[:-1]) == {"_1": EXTENSIVE_JSON}


@pytest.mark.aws_verified
@s3_aws_verified
def test_nested_json__select_all(bucket_name=None):
    client = boto3.client("s3", "us-east-1")
    create_test_files(bucket_name)
    content = client.select_object_content(
        Bucket=bucket_name,
        Key="nested.json",
        Expression="select * from s3object s",
        ExpressionType="SQL",
        InputSerialization={"JSON": {"Type": "DOCUMENT"}},
        OutputSerialization={"JSON": {"RecordDelimiter": ","}},
    )
    result = list(content["Payload"])
    records = [res for res in result if "Records" in res][0]["Records"][
        "Payload"
    ].decode("utf-8")

    # For some reason, AWS returns records with a comma at the end
    assert records[-1] == ","

    assert json.loads(records[:-1]) == NESTED_JSON
