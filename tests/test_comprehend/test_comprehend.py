"""Unit tests for comprehend-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import
from botocore.exceptions import ClientError
from moto import mock_comprehend

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


INPUT_DATA_CONFIG = {
    "DataFormat": "COMPREHEND_CSV",
    "Documents": {
        "InputFormat": "ONE_DOC_PER_LINE",
        "S3Uri": "s3://tf-acc-test-1726651689102157637/documents.txt",
    },
    "EntityList": {"S3Uri": "s3://tf-acc-test-1726651689102157637/entitylist.csv"},
    "EntityTypes": [{"Type": "ENGINEER"}, {"Type": "MANAGER"}],
}


@mock_comprehend
def test_list_entity_recognizers():
    client = boto3.client("comprehend", region_name="us-east-2")

    resp = client.list_entity_recognizers()
    resp.should.have.key("EntityRecognizerPropertiesList").equals([])

    client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="myname",
        VersionName="version1",
    )

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "unknown"})
    resp.should.have.key("EntityRecognizerPropertiesList").equals([])

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "myname"})
    resp.should.have.key("EntityRecognizerPropertiesList").length_of(1)

    client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="myname",
        VersionName="version2",
    )

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "myname"})
    resp.should.have.key("EntityRecognizerPropertiesList").length_of(2)


@mock_comprehend
def test_create_entity_recognizer():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )

    resp.should.have.key("EntityRecognizerArn")


@mock_comprehend
def test_create_entity_recognizer_without_version():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
    )

    resp.should.have.key("EntityRecognizerArn")
    resp["EntityRecognizerArn"].should.equal(
        "arn:aws:comprehend:ap-southeast-1:123456789012:entity-recognizer/tf-acc-test-1726651689102157637"
    )


@mock_comprehend
def test_create_entity_recognizer_with_tags():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        Tags=[{"Key": "k1", "Value": "v1"}],
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
    )["EntityRecognizerArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceArn").equals(arn)
    resp.should.have.key("Tags").equals([{"Key": "k1", "Value": "v1"}])


@mock_comprehend
def test_describe_entity_recognizer():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["EntityRecognizerArn"]

    resp = client.describe_entity_recognizer(EntityRecognizerArn=arn)
    resp.should.have.key("EntityRecognizerProperties")
    props = resp["EntityRecognizerProperties"]

    props.should.have.key("EntityRecognizerArn").equals(arn)
    props.should.have.key("LanguageCode").equals("en")
    props.should.have.key("Status").equals("TRAINED")
    props.should.have.key("InputDataConfig").equals(INPUT_DATA_CONFIG)
    props.should.have.key("DataAccessRoleArn").equals("iam_role_with_20_chars")
    props.should.have.key("VersionName").equals("terraform-20221003201727469000000002")


@mock_comprehend
def test_describe_unknown_recognizer():
    client = boto3.client("comprehend", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_entity_recognizer(EntityRecognizerArn="unknown")
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "RESOURCE_NOT_FOUND: Could not find specified resource."
    )


@mock_comprehend
def test_stop_training_entity_recognizer():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["EntityRecognizerArn"]
    client.stop_training_entity_recognizer(EntityRecognizerArn=arn)

    props = client.describe_entity_recognizer(EntityRecognizerArn=arn)[
        "EntityRecognizerProperties"
    ]
    props.should.have.key("Status").equals("TRAINED")


@mock_comprehend
def test_list_tags_for_resource():
    client = boto3.client("comprehend", region_name="us-east-2")
    arn = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["EntityRecognizerArn"]

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("ResourceArn").equals(arn)
    resp.should.have.key("Tags").equals([])

    client.tag_resource(ResourceArn=arn, Tags=[{"Key": "k1", "Value": "v1"}])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("Tags").equals([{"Key": "k1", "Value": "v1"}])

    client.untag_resource(ResourceArn=arn, TagKeys=["k1"])
    resp = client.list_tags_for_resource(ResourceArn=arn)
    resp.should.have.key("Tags").equals([])


@mock_comprehend
def test_delete_entity_recognizer():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["EntityRecognizerArn"]

    client.delete_entity_recognizer(EntityRecognizerArn=arn)

    with pytest.raises(ClientError) as exc:
        client.describe_entity_recognizer(EntityRecognizerArn=arn)
    err = exc.value.response["Error"]
    err["Code"].should.equal("ResourceNotFoundException")
    err["Message"].should.equal(
        "RESOURCE_NOT_FOUND: Could not find specified resource."
    )
