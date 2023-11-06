import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.comprehend.models import (
    CANNED_DETECT_RESPONSE,
    CANNED_PHRASES_RESPONSE,
    CANNED_SENTIMENT_RESPONSE,
)

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


@mock_aws
def test_list_entity_recognizers():
    client = boto3.client("comprehend", region_name="us-east-2")

    resp = client.list_entity_recognizers()
    assert resp["EntityRecognizerPropertiesList"] == []

    client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="myname",
        VersionName="version1",
    )

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "unknown"})
    assert resp["EntityRecognizerPropertiesList"] == []

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "myname"})
    assert len(resp["EntityRecognizerPropertiesList"]) == 1

    client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="myname",
        VersionName="version2",
    )

    resp = client.list_entity_recognizers(Filter={"RecognizerName": "myname"})
    assert len(resp["EntityRecognizerPropertiesList"]) == 2


@mock_aws
def test_create_entity_recognizer():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )

    assert "EntityRecognizerArn" in resp


@mock_aws
def test_create_entity_recognizer_without_version():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_entity_recognizer(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="tf-acc-test-1726651689102157637",
    )

    assert "EntityRecognizerArn" in resp
    assert (
        resp["EntityRecognizerArn"]
        == "arn:aws:comprehend:ap-southeast-1:123456789012:entity-recognizer/tf-acc-test-1726651689102157637"
    )


@mock_aws
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
    assert resp["ResourceArn"] == arn
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]


@mock_aws
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
    assert "EntityRecognizerProperties" in resp
    props = resp["EntityRecognizerProperties"]

    assert props["EntityRecognizerArn"] == arn
    assert props["LanguageCode"] == "en"
    assert props["Status"] == "TRAINED"
    assert props["InputDataConfig"] == INPUT_DATA_CONFIG
    assert props["DataAccessRoleArn"] == "iam_role_with_20_chars"
    assert props["VersionName"] == "terraform-20221003201727469000000002"


@mock_aws
def test_describe_unknown_recognizer():
    client = boto3.client("comprehend", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.describe_entity_recognizer(EntityRecognizerArn="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "RESOURCE_NOT_FOUND: Could not find specified resource."


@mock_aws
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
    assert props["Status"] == "TRAINED"


@mock_aws
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
    assert resp["ResourceArn"] == arn
    assert resp["Tags"] == []

    client.tag_resource(ResourceArn=arn, Tags=[{"Key": "k1", "Value": "v1"}])

    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == [{"Key": "k1", "Value": "v1"}]

    client.untag_resource(ResourceArn=arn, TagKeys=["k1"])
    resp = client.list_tags_for_resource(ResourceArn=arn)
    assert resp["Tags"] == []


@mock_aws
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
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "RESOURCE_NOT_FOUND: Could not find specified resource."


@mock_aws
def test_detect_pii_entities():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"

    # Execute
    result = client.detect_pii_entities(Text=sample_text, LanguageCode="en")

    # Verify
    assert "Entities" in result
    assert result["Entities"] == CANNED_DETECT_RESPONSE


@mock_aws
def test_detect_pii_entities_invalid_languages():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"
    language = "es"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_pii_entities(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == f"Value '{language}' at 'languageCode'failed to satisfy constraint: "
        f"Member must satisfy enum value set: [en]"
    )


@mock_aws
def test_detect_pii_entities_text_too_large():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    size = 100001
    sample_text = "x" * size
    language = "en"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_pii_entities(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "TextSizeLimitExceededException"
    assert (
        err["Message"]
        == "Input text size exceeds limit. Max length of request text allowed is 100000 bytes "
        f"while in this request the text size is {size} bytes"
    )


@mock_aws
def test_detect_key_phrases():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"

    # Execute
    result = client.detect_key_phrases(Text=sample_text, LanguageCode="en")

    # Verify
    assert "KeyPhrases" in result
    assert result["KeyPhrases"] == CANNED_PHRASES_RESPONSE


@mock_aws
def test_detect_key_phrases_invalid_languages():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"
    language = "blah"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_key_phrases(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == f"Value '{language}' at 'languageCode'failed to satisfy constraint: "
        f"Member must satisfy enum value set: [ar, hi, ko, zh-TW, ja, zh, de, pt, en, it, fr, es]"
    )


@mock_aws
def test_detect_detect_key_phrases_text_too_large():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    size = 100002
    sample_text = "x" * size
    language = "en"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_key_phrases(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "TextSizeLimitExceededException"
    assert (
        err["Message"]
        == "Input text size exceeds limit. Max length of request text allowed is 100000 bytes "
        f"while in this request the text size is {size} bytes"
    )


@mock_aws
def test_detect_sentiment():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"

    # Execute
    result = client.detect_sentiment(Text=sample_text, LanguageCode="en")

    # Verify
    del result["ResponseMetadata"]
    assert result == CANNED_SENTIMENT_RESPONSE


@mock_aws
def test_detect_sentiment_invalid_languages():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    sample_text = "Doesn't matter what we send, we will get a canned response"
    language = "blah"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_sentiment(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == f"Value '{language}' at 'languageCode'failed to satisfy constraint: "
        "Member must satisfy enum value set: [ar, hi, ko, zh-TW, ja, zh, de, pt, en, it, fr, es]"
    )


@mock_aws
def test_detect_sentiment_text_too_large():
    # Setup
    client = boto3.client("comprehend", region_name="eu-west-1")
    size = 5001
    sample_text = "x" * size
    language = "en"

    # Execute
    with pytest.raises(ClientError) as exc:
        client.detect_sentiment(Text=sample_text, LanguageCode=language)

    # Verify
    err = exc.value.response["Error"]
    assert err["Code"] == "TextSizeLimitExceededException"
    assert (
        err["Message"]
        == "Input text size exceeds limit. Max length of request text allowed is 100000 bytes while "
        f"in this request the text size is {size} bytes"
    )
