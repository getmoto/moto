"""Unit tests for rekognition-supported APIs."""

import random
import string

import boto3

from moto import mock_aws
from moto.moto_api._internal import mock_random

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_start_face_search():
    client = boto3.client("rekognition", region_name="ap-southeast-1")
    collection_id = "collection_id"
    video = {
        "S3Object": {
            "Bucket": "bucket",
            "Name": "key",
        }
    }

    resp = client.start_face_search(CollectionId=collection_id, Video=video)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "JobId" in resp


@mock_aws
def test_start_text_detection():
    client = boto3.client("rekognition", region_name="ap-southeast-1")
    video = {
        "S3Object": {
            "Bucket": "bucket",
            "Name": "key",
        }
    }

    resp = client.start_text_detection(Video=video)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "JobId" in resp


@mock_aws
def test_compare_faces():
    client = boto3.client("rekognition", region_name="ap-southeast-1")
    sourceimage = {
        "S3Object": {"Bucket": "string", "Name": "string", "Version": "string"}
    }
    targetimage = {
        "S3Object": {"Bucket": "string", "Name": "string", "Version": "string"}
    }

    resp = client.compare_faces(
        SimilarityThreshold=80, SourceImage=sourceimage, TargetImage=targetimage
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "FaceMatches" in resp


@mock_aws
def test_detect_labels():
    client = boto3.client("rekognition", region_name="ap-southeast-1")

    resp = client.detect_labels(
        Image={"S3Object": {"Bucket": "string", "Name": "name.jpg"}}, MaxLabels=10
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "Labels" in resp


@mock_aws
def test_detect_text():
    client = boto3.client("rekognition", region_name="ap-southeast-1")

    resp = client.detect_text(
        Image={"S3Object": {"Bucket": "string", "Name": "name.jpg"}}
    )

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert "TextDetections" in resp


@mock_aws
def test_get_face_search():
    client = boto3.client("rekognition", region_name="us-east-2")
    job_id = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(64)
    )

    resp = client.get_face_search(JobId=job_id)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert resp["JobStatus"] == "SUCCEEDED"
    assert (
        resp["Persons"][0]["FaceMatches"][0]["Face"]["ExternalImageId"] == "Dave_Bloggs"
    )


@mock_aws
def test_get_text_detection():
    client = boto3.client("rekognition", region_name="us-east-2")
    job_id = "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(64)
    )

    resp = client.get_text_detection(JobId=job_id)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    assert resp["JobStatus"] == "SUCCEEDED"
    assert resp["TextDetections"][0]["TextDetection"]["DetectedText"] == "Hello world"


@mock_aws
def test_detect_custom_labels():
    client = boto3.client("rekognition", region_name="us-east-2")
    resp = client.detect_custom_labels(
        Image={"S3Object": {"Bucket": "string", "Name": "name.jpg"}},
        MaxResults=10,
        MinConfidence=80,
        ProjectVersionArn=mock_random.get_random_string(),
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["CustomLabels"][0]["Name"] == "MyLogo"
