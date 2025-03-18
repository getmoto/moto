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

OUTPUT_DATA_CONFIG = {
    "S3Uri": "string",
    "KmsKeyId": "string",
    "FlywheelStatsS3Prefix": "string",
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
def test_create_document_classifier():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        ClientRequestToken="unique-token",
        VolumeKmsKeyId="kms-key-id",
        VpcConfig={"SecurityGroupIds": ["sg-12345678"], "Subnets": ["subnet-12345678"]},
        Mode="MULTI_CLASS",
        ModelKmsKeyId="model-kms-key-id",
        ModelPolicy="model-policy",
    )

    assert "DocumentClassifierArn" in resp


@mock_aws
def test_describe_document_classifier():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["DocumentClassifierArn"]

    resp = client.describe_document_classifier(DocumentClassifierArn=arn)
    assert "DocumentClassifierProperties" in resp
    props = resp["DocumentClassifierProperties"]

    assert props["DocumentClassifierArn"] == arn
    assert props["LanguageCode"] == "en"
    assert props["Status"] == "TRAINED"
    assert props["InputDataConfig"] == INPUT_DATA_CONFIG
    assert props["DataAccessRoleArn"] == "iam_role_with_20_chars"


@mock_aws
def test_list_document_classifiers():
    client = boto3.client("comprehend", region_name="us-east-2")

    resp = client.list_document_classifiers()
    assert resp["DocumentClassifierPropertiesList"] == []

    client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="myname",
        VersionName="version1",
    )

    resp = client.list_document_classifiers(
        Filter={"DocumentClassifierName": "unknown"}
    )
    assert resp["DocumentClassifierPropertiesList"] == []

    resp = client.list_document_classifiers(Filter={"DocumentClassifierName": "myname"})
    assert len(resp["DocumentClassifierPropertiesList"]) == 1

    client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="myname",
        VersionName="version2",
    )

    resp = client.list_document_classifiers(Filter={"DocumentClassifierName": "myname"})
    assert len(resp["DocumentClassifierPropertiesList"]) == 2


@mock_aws
def test_delete_document_classifier():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["DocumentClassifierArn"]

    client.delete_document_classifier(DocumentClassifierArn=arn)

    with pytest.raises(ClientError) as exc:
        client.describe_document_classifier(DocumentClassifierArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "RESOURCE_NOT_FOUND: Could not find specified resource."


@mock_aws
def test_stop_training_document_classifier():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_document_classifier(
        DataAccessRoleArn="iam_role_with_20_chars",
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        DocumentClassifierName="tf-acc-test-1726651689102157637",
        VersionName="terraform-20221003201727469000000002",
    )["DocumentClassifierArn"]
    client.stop_training_document_classifier(DocumentClassifierArn=arn)

    props = client.describe_document_classifier(DocumentClassifierArn=arn)[
        "DocumentClassifierProperties"
    ]
    assert props["Status"] == "STOP_REQUESTED"


@mock_aws
def test_create_endpoint():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="tf-acc-test-1726651689102157637",
        ClientRequestToken="unique-token",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )

    assert "EndpointArn" in resp


@mock_aws
def test_describe_endpoint():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="tf-acc-test-1726651689102157637",
        ClientRequestToken="unique-token",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )["EndpointArn"]

    resp = client.describe_endpoint(EndpointArn=arn)
    assert "EndpointProperties" in resp
    props = resp["EndpointProperties"]

    assert props["EndpointArn"] == arn
    assert (
        props["ModelArn"]
        == "arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637"
    )
    assert props["Status"] == "CREATING"
    assert props["DesiredInferenceUnits"] == 123
    assert props["CreationTime"] == props["LastModifiedTime"]
    assert (
        props["FlywheelArn"]
        == "arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637"
    )


@mock_aws
def test_delete_endpoint():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="tf-acc-test-1726651689102157637",
        ClientRequestToken="unique-token",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )["EndpointArn"]

    client.delete_endpoint(EndpointArn=arn)

    with pytest.raises(ClientError) as exc:
        client.describe_endpoint(EndpointArn=arn)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "RESOURCE_NOT_FOUND: Could not find specified resource."


@mock_aws
def test_list_endpoints():
    client = boto3.client("comprehend", region_name="us-east-2")

    resp = client.list_endpoints()
    assert resp["EndpointPropertiesList"] == []

    client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="myname",
        ClientRequestToken="unique-token",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )

    resp = client.list_endpoints(Filter={"EndpointName": "unknown"})
    assert resp["EndpointPropertiesList"] == []

    resp = client.list_endpoints(Filter={"EndpointName": "myname"})
    assert len(resp["EndpointPropertiesList"]) == 1

    client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="myname",
        ClientRequestToken="unique-token",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )

    resp = client.list_endpoints(Filter={"EndpointName": "myname"})
    assert len(resp["EndpointPropertiesList"]) == 2


@mock_aws
def test_update_endpoint():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_endpoint(
        ModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredInferenceUnits=123,
        EndpointName="tf-acc-test-1726651689102157637",
        ClientRequestToken="unique-token",
        DesiredModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DesiredDataAccessRoleArn="iam_role_with_20_chars",
        FlywheelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
    )["EndpointArn"]

    client.update_endpoint(
        EndpointArn=arn,
        DesiredInferenceUnits=456,
    )

    resp = client.describe_endpoint(EndpointArn=arn)
    assert (
        resp["DesiredModelArn"]
        == "arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637"
    )


@mock_aws
def test_create_flywheel():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    resp = client.create_flywheel(
        ActiveModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig=INPUT_DATA_CONFIG,
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri="s3://tf-acc-test-1726651689102157637/documents.txt",
        DataSecurityConfig={"KmsKeyId": "kms-key-id"},
        ClientRequestToken="unique-token",
    )

    assert "FlywheelArn" in resp


@mock_aws
def test_describe_flywheel():
    client = boto3.client("comprehend", region_name="eu-west-1")
    arn = client.create_flywheel(
        ActiveModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig=INPUT_DATA_CONFIG,
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri="s3://tf-acc-test-1726651689102157637/documents.txt",
        DataSecurityConfig={"KmsKeyId": "kms-key-id"},
        ClientRequestToken="unique-token",
    )["FlywheelArn"]

    resp = client.describe_flywheel(FlywheelArn=arn)
    assert "FlywheelProperties" in resp
    props = resp["FlywheelProperties"]
    assert props["FlywheelArn"] == arn
    assert (
        props["ActiveModelArn"]
        == "arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637"
    )
    assert props["Status"] == "CREATING"
    assert props["DataAccessRoleArn"] == "iam_role_with_20_chars"
    assert props["ModelType"] == "DOCUMENT_CLASSIFIER"
    assert (
        props["DataLakeS3Uri"] == "s3://tf-acc-test-1726651689102157637/documents.txt"
    )
    assert props["DataSecurityConfig"] == {"KmsKeyId": "kms-key-id"}


@mock_aws
def test_list_flywheels():
    client = boto3.client("comprehend", region_name="us-east-2")

    resp = client.list_flywheels()
    assert resp["FlywheelPropertiesList"] == []

    client.create_flywheel(
        ActiveModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig=INPUT_DATA_CONFIG,
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri="s3://tf-acc-test-1726651689102157637/documents.txt",
        DataSecurityConfig={"KmsKeyId": "kms-key-id"},
        ClientRequestToken="unique-token",
    )

    resp = client.list_flywheels(Filter={"FlywheelArn": "unknown"})
    assert resp["FlywheelPropertiesList"] == []

    resp = client.list_flywheels(Filter={"FlywheelArn": "myname"})
    assert len(resp["FlywheelPropertiesList"]) == 1


@mock_aws
def test_delete_flywheel():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_flywheel(
        ActiveModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig=INPUT_DATA_CONFIG,
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri="s3://tf-acc-test-1726651689102157637/documents.txt",
        DataSecurityConfig={"KmsKeyId": "kms-key-id"},
        ClientRequestToken="unique-token",
    )["FlywheelArn"]

    client.delete_flywheel(FlywheelArn=arn)
    assert client.list_flywheels()["FlywheelPropertiesList"] == []


@mock_aws
def test_start_flywheel_iteration():
    client = boto3.client("comprehend", region_name="ap-southeast-1")
    arn = client.create_flywheel(
        ActiveModelArn="arn:aws:comprehend:ap-southeast-1:123456789012:document-classifier/tf-acc-test-1726651689102157637",
        DataAccessRoleArn="iam_role_with_20_chars",
        TaskConfig=INPUT_DATA_CONFIG,
        ModelType="DOCUMENT_CLASSIFIER",
        DataLakeS3Uri="s3://tf-acc-test-1726651689102157637/documents.txt",
        DataSecurityConfig={"KmsKeyId": "kms-key-id"},
        ClientRequestToken="unique-token",
    )["FlywheelArn"]

    resp = client.start_flywheel_iteration(FlywheelArn=arn)
    assert "FlyWheelIterationId" in resp


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
