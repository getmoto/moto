import boto3

from moto import mock_aws

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
}

DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG = {
    "DataFormat": "COMPREHEND_CSV",
    "S3Uri": "s3://fake-bucket/documents.csv",
    "TestS3Uri": "s3://fake-bucket/test-documents.csv",
    "LabelDelimiter": ",",
    "AugmentedManifests": [
        {
            "S3Uri": "s3://fake-bucket/augmented-manifest.json",
            "Split": "TRAIN",
            "AttributeNames": [
                "Attribute1",
                "Attribute2",
            ],
            "AnnotationDataS3Uri": "s3://fake-bucket/annotations.json",
            "SourceDocumentsS3Uri": "s3://fake-bucket/source-documents/",
            "DocumentType": "PLAIN_TEXT_DOCUMENT",
        },
    ],
    "DocumentType": "PLAIN_TEXT_DOCUMENT",
    "Documents": {
        "S3Uri": "s3://fake-bucket/documents/",
        "TestS3Uri": "s3://fake-bucket/test-documents/",
    },
    "DocumentReaderConfig": {
        "DocumentReadAction": "TEXTRACT_DETECT_DOCUMENT_TEXT",
        "DocumentReadMode": "SERVICE_DEFAULT",
        "FeatureTypes": [
            "TABLES",
            "FORMS",
        ],
    },
}


@mock_aws
def test_pii_entities_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="us-east-1")
    job_name = "test-pii-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"
    start_resp = client.start_pii_entities_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
        LanguageCode="en",
        Mode="ONLY_REDACTION",
        RedactionConfig={"MaskCharacter": "*", "MaskMode": "MASK"},
    )
    job_id = start_resp["JobId"]
    assert job_id
    assert start_resp["JobStatus"] == "SUBMITTED"

    desc_resp = client.describe_pii_entities_detection_job(JobId=job_id)
    props = desc_resp["PiiEntitiesDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["JobStatus"] == "SUBMITTED"
    assert props["Mode"] == "ONLY_REDACTION"

    list_resp = client.list_pii_entities_detection_jobs(Filter={"JobName": job_name})
    assert len(list_resp["PiiEntitiesDetectionJobPropertiesList"]) == 1

    client.stop_pii_entities_detection_job(JobId=job_id)
    desc_resp = client.describe_pii_entities_detection_job(JobId=job_id)
    assert (
        desc_resp["PiiEntitiesDetectionJobProperties"]["JobStatus"] == "STOP_REQUESTED"
    )


@mock_aws
def test_key_phrases_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="us-west-2")
    job_name = "test-key-phrases-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    start_resp = client.start_key_phrases_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
        LanguageCode="en",
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_key_phrases_detection_job(JobId=job_id)
    props = desc_resp["KeyPhrasesDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["JobName"] == job_name
    assert props["LanguageCode"] == "en"

    list_resp = client.list_key_phrases_detection_jobs()
    assert len(list_resp["KeyPhrasesDetectionJobPropertiesList"]) == 1

    client.stop_key_phrases_detection_job(JobId=job_id)
    desc_resp = client.describe_key_phrases_detection_job(JobId=job_id)
    assert (
        desc_resp["KeyPhrasesDetectionJobProperties"]["JobStatus"] == "STOP_REQUESTED"
    )


@mock_aws
def test_sentiment_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="ca-central-1")
    job_name = "test-sentiment-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    start_resp = client.start_sentiment_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
        LanguageCode="es",
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_sentiment_detection_job(JobId=job_id)
    props = desc_resp["SentimentDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["JobName"] == job_name
    assert props["LanguageCode"] == "es"

    list_resp = client.list_sentiment_detection_jobs()
    assert len(list_resp["SentimentDetectionJobPropertiesList"]) == 1

    client.stop_sentiment_detection_job(JobId=job_id)
    desc_resp = client.describe_sentiment_detection_job(JobId=job_id)
    assert desc_resp["SentimentDetectionJobProperties"]["JobStatus"] == "STOP_REQUESTED"


@mock_aws
def test_targeted_sentiment_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="eu-central-1")
    job_name = "test-targeted-sentiment-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"
    start_resp = client.start_targeted_sentiment_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
        LanguageCode="en",
    )
    job_id = start_resp["JobId"]
    assert job_id
    assert start_resp["JobStatus"] == "SUBMITTED"

    desc_resp = client.describe_targeted_sentiment_detection_job(JobId=job_id)
    props = desc_resp["TargetedSentimentDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["JobName"] == job_name
    assert props["JobStatus"] == "SUBMITTED"

    list_resp = client.list_targeted_sentiment_detection_jobs()
    assert len(list_resp["TargetedSentimentDetectionJobPropertiesList"]) == 1
    assert (
        list_resp["TargetedSentimentDetectionJobPropertiesList"][0]["JobId"] == job_id
    )

    client.stop_targeted_sentiment_detection_job(JobId=job_id)
    desc_resp = client.describe_targeted_sentiment_detection_job(JobId=job_id)
    assert (
        desc_resp["TargetedSentimentDetectionJobProperties"]["JobStatus"]
        == "STOP_REQUESTED"
    )


@mock_aws
def test_dominant_language_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="us-east-1")
    job_name = "test-dominant-language-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    start_resp = client.start_dominant_language_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
    )
    job_id = start_resp["JobId"]
    assert job_id
    assert start_resp["JobStatus"] == "SUBMITTED"

    desc_resp = client.describe_dominant_language_detection_job(JobId=job_id)
    props = desc_resp["DominantLanguageDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["JobName"] == job_name
    assert props["JobStatus"] == "SUBMITTED"
    assert props["DataAccessRoleArn"] == role_arn

    list_resp = client.list_dominant_language_detection_jobs()
    assert len(list_resp["DominantLanguageDetectionJobPropertiesList"]) == 1
    assert list_resp["DominantLanguageDetectionJobPropertiesList"][0]["JobId"] == job_id

    client.stop_dominant_language_detection_job(JobId=job_id)
    desc_resp = client.describe_dominant_language_detection_job(JobId=job_id)
    assert (
        desc_resp["DominantLanguageDetectionJobProperties"]["JobStatus"]
        == "STOP_REQUESTED"
    )


@mock_aws
def test_entities_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="eu-west-1")
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    recognizer_arn = client.create_entity_recognizer(
        DataAccessRoleArn=role_arn,
        InputDataConfig=INPUT_DATA_CONFIG,
        LanguageCode="en",
        RecognizerName="test-recognizer-for-job",
    )["EntityRecognizerArn"]

    start_resp = client.start_entities_detection_job(
        EntityRecognizerArn=recognizer_arn,
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        LanguageCode="en",
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_entities_detection_job(JobId=job_id)
    props = desc_resp["EntitiesDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["EntityRecognizerArn"] == recognizer_arn

    list_resp = client.list_entities_detection_jobs(Filter={"JobStatus": "SUBMITTED"})
    assert len(list_resp["EntitiesDetectionJobPropertiesList"]) == 1

    client.stop_entities_detection_job(JobId=job_id)
    desc_resp = client.describe_entities_detection_job(JobId=job_id)
    assert desc_resp["EntitiesDetectionJobProperties"]["JobStatus"] == "STOP_REQUESTED"


@mock_aws
def test_topics_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="ap-southeast-2")
    job_name = "test-topics-job"
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    start_resp = client.start_topics_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        JobName=job_name,
        NumberOfTopics=10,
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_topics_detection_job(JobId=job_id)
    props = desc_resp["TopicsDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["NumberOfTopics"] == 10

    list_resp = client.list_topics_detection_jobs()
    assert len(list_resp["TopicsDetectionJobPropertiesList"]) == 1


@mock_aws
def test_document_classification_job_lifecycle():
    client = boto3.client("comprehend", region_name="us-west-2")
    role_arn = "arn:aws:iam::123456789012:role/testing-role"

    classifier_arn = client.create_document_classifier(
        DocumentClassifierName="test-classifier-for-job",
        VersionName="v1",
        DataAccessRoleArn=role_arn,
        InputDataConfig=DOCUMENT_CLASSIFIER_INPUT_DATA_CONFIG,
        LanguageCode="en",
    )["DocumentClassifierArn"]

    start_resp = client.start_document_classification_job(
        DocumentClassifierArn=classifier_arn,
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_document_classification_job(JobId=job_id)
    props = desc_resp["DocumentClassificationJobProperties"]
    assert props["JobId"] == job_id
    assert props["DocumentClassifierArn"] == classifier_arn

    list_resp = client.list_document_classification_jobs()
    assert len(list_resp["DocumentClassificationJobPropertiesList"]) == 1


@mock_aws
def test_events_detection_job_lifecycle():
    client = boto3.client("comprehend", region_name="ca-central-1")
    role_arn = "arn:aws:iam::123456789012:role/testing-role"
    event_types = ["EVENT_A", "EVENT_B"]

    start_resp = client.start_events_detection_job(
        InputDataConfig=INPUT_DATA_CONFIG["Documents"],
        OutputDataConfig=OUTPUT_DATA_CONFIG,
        DataAccessRoleArn=role_arn,
        LanguageCode="en",
        TargetEventTypes=event_types,
    )
    job_id = start_resp["JobId"]
    assert job_id

    desc_resp = client.describe_events_detection_job(JobId=job_id)
    props = desc_resp["EventsDetectionJobProperties"]
    assert props["JobId"] == job_id
    assert props["TargetEventTypes"] == event_types

    list_resp = client.list_events_detection_jobs()
    assert len(list_resp["EventsDetectionJobPropertiesList"]) == 1

    client.stop_events_detection_job(JobId=job_id)
    desc_resp = client.describe_events_detection_job(JobId=job_id)
    assert desc_resp["EventsDetectionJobProperties"]["JobStatus"] == "STOP_REQUESTED"
