"""Unit tests for cloudtrail-supported APIs."""
import boto3
import pytest
import sure  # noqa # pylint: disable=unused-import

from botocore.exceptions import ClientError
from datetime import datetime
from moto import mock_cloudtrail, mock_s3, mock_sns
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from uuid import uuid4


@mock_s3
@mock_cloudtrail
def test_create_trail_without_bucket():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name="mytrailname", S3BucketName="specificweirdbucketthatdoesnotexist"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("S3BucketDoesNotExistException")
    err["Message"].should.equal(
        "S3 bucket specificweirdbucketthatdoesnotexist does not exist!"
    )


@pytest.mark.parametrize(
    "name,message",
    [
        (
            "a",
            "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 1 characters.",
        ),
        (
            "aa",
            "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 2 characters.",
        ),
        (
            "a" * 129,
            "Trail name too long. Maximum allowed length: 128 characters. Specified name length: 129 characters.",
        ),
        ("trail!", "Trail name must ends with a letter or number."),
        (
            "my#trail",
            "Trail name or ARN can only contain uppercase letters, lowercase letters, numbers, periods (.), hyphens (-), and underscores (_).",
        ),
        ("-trail", "Trail name must starts with a letter or number."),
    ],
)
@mock_cloudtrail
def test_create_trail_invalid_name(name, message):
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name=name, S3BucketName="specificweirdbucketthatdoesnotexist"
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidTrailNameException")
    err["Message"].should.equal(message)


@mock_cloudtrail
@mock_s3
def test_create_trail_simple():
    bucket_name, resp, trail_name = create_trail_simple()
    resp.should.have.key("Name").equal(trail_name)
    resp.should.have.key("S3BucketName").equal(bucket_name)
    resp.shouldnt.have.key("S3KeyPrefix")
    resp.shouldnt.have.key("SnsTopicName")
    resp.shouldnt.have.key("SnsTopicARN")
    resp.should.have.key("IncludeGlobalServiceEvents").equal(True)
    resp.should.have.key("IsMultiRegionTrail").equal(False)
    resp.should.have.key("TrailARN").equal(
        f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{trail_name}"
    )
    resp.should.have.key("LogFileValidationEnabled").equal(False)
    resp.should.have.key("IsOrganizationTrail").equal(False)
    return resp


def create_trail_simple(region_name="us-east-1"):
    client = boto3.client("cloudtrail", region_name=region_name)
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    trail_name = str(uuid4())
    resp = client.create_trail(Name=trail_name, S3BucketName=bucket_name)
    return bucket_name, resp, trail_name


@mock_cloudtrail
def test_create_trail_multi_but_not_global():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name="mytrailname",
            S3BucketName="non-existent",
            IncludeGlobalServiceEvents=False,
            IsMultiRegionTrail=True,
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidParameterCombinationException")
    # Note that this validation occurs before the S3 bucket is validated
    err["Message"].should.equal(
        "Multi-Region trail must include global service events."
    )


@mock_cloudtrail
@mock_s3
@mock_sns
def test_create_trail_with_nonexisting_topic():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name="mytrailname",
            S3BucketName=bucket_name,
            SnsTopicName="nonexistingtopic",
        )
    err = exc.value.response["Error"]
    err["Code"].should.equal("InsufficientSnsTopicPolicyException")
    err["Message"].should.equal(
        "SNS Topic does not exist or the topic policy is incorrect!"
    )


@mock_cloudtrail
@mock_s3
@mock_sns
def test_create_trail_advanced():
    bucket_name, resp, sns_topic_name, trail_name = create_trail_advanced()
    resp.should.have.key("Name").equal(trail_name)
    resp.should.have.key("S3BucketName").equal(bucket_name)
    resp.should.have.key("S3KeyPrefix").equal("s3kp")
    resp.should.have.key("SnsTopicName").equal(sns_topic_name)
    resp.should.have.key("SnsTopicARN").equal(
        f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:{sns_topic_name}"
    )
    resp.should.have.key("IncludeGlobalServiceEvents").equal(True)
    resp.should.have.key("IsMultiRegionTrail").equal(True)
    resp.should.have.key("TrailARN").equal(
        f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{trail_name}"
    )
    resp.should.have.key("LogFileValidationEnabled").equal(True)
    resp.should.have.key("IsOrganizationTrail").equal(True)
    resp.should.have.key("CloudWatchLogsLogGroupArn").equals("cwllga")
    resp.should.have.key("CloudWatchLogsRoleArn").equals("cwlra")
    resp.should.have.key("KmsKeyId").equals("kki")


def create_trail_advanced(region_name="us-east-1"):
    client = boto3.client("cloudtrail", region_name=region_name)
    s3 = boto3.client("s3", region_name="us-east-1")
    sns = boto3.client("sns", region_name=region_name)
    bucket_name = str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    sns_topic_name = "cloudtrailtopic"
    sns.create_topic(Name=sns_topic_name)
    trail_name = str(uuid4())
    resp = client.create_trail(
        Name=trail_name,
        S3BucketName=bucket_name,
        S3KeyPrefix="s3kp",
        SnsTopicName=sns_topic_name,
        IncludeGlobalServiceEvents=True,
        IsMultiRegionTrail=True,
        EnableLogFileValidation=True,
        IsOrganizationTrail=True,
        CloudWatchLogsLogGroupArn="cwllga",
        CloudWatchLogsRoleArn="cwlra",
        KmsKeyId="kki",
        TagsList=[{"Key": "tk", "Value": "tv"}, {"Key": "tk2", "Value": "tv2"}],
    )
    return bucket_name, resp, sns_topic_name, trail_name


@mock_cloudtrail
def test_get_trail_with_one_char():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail(Name="?")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidTrailNameException")
    err["Message"].should.equal(
        "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 1 characters."
    )


@mock_cloudtrail
def test_get_trail_unknown():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail(Name="unknowntrail")
    err = exc.value.response["Error"]
    err["Code"].should.equal("TrailNotFoundException")
    err["Message"].should.equal(
        f"Unknown trail: unknowntrail for the user: {ACCOUNT_ID}"
    )


@mock_cloudtrail
def test_get_trail():
    test_create_trail_simple()
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name = create_trail_simple()
    trail = client.get_trail(Name=name)["Trail"]
    trail.should.have.key("Name").equal(name)
    trail.should.have.key("IncludeGlobalServiceEvents").equal(True)
    trail.should.have.key("IsMultiRegionTrail").equal(False)
    trail.should.have.key("TrailARN").equal(
        f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{name}"
    )


@mock_cloudtrail
def test_get_trail_status_with_one_char():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail_status(Name="?")
    err = exc.value.response["Error"]
    err["Code"].should.equal("InvalidTrailNameException")
    err["Message"].should.equal(
        "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 1 characters."
    )


@mock_cloudtrail
def test_get_trail_status_unknown_trail():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail_status(Name="unknowntrail")
    err = exc.value.response["Error"]
    err["Code"].should.equal("TrailNotFoundException")
    err["Message"].should.equal(
        f"Unknown trail: arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/unknowntrail for the user: {ACCOUNT_ID}"
    )


@mock_cloudtrail
@mock_s3
def test_get_trail_status_inactive():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, trail_name = create_trail_simple()
    status = client.get_trail_status(Name=trail_name)
    status.should.have.key("IsLogging").equal(False)
    status.should.have.key("LatestDeliveryAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptSucceeded").equal("")
    status.should.have.key("LatestDeliveryAttemptSucceeded").equal("")
    status.should.have.key("TimeLoggingStarted").equal("")
    status.should.have.key("TimeLoggingStopped").equal("")
    status.shouldnt.have.key("StartLoggingTime")


@mock_cloudtrail
@mock_s3
def test_get_trail_status_arn_inactive():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, resp, _ = create_trail_simple()
    status = client.get_trail_status(Name=resp["TrailARN"])
    status.should.have.key("IsLogging").equal(False)
    status.should.have.key("LatestDeliveryAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptSucceeded").equal("")
    status.should.have.key("LatestDeliveryAttemptSucceeded").equal("")
    status.should.have.key("TimeLoggingStarted").equal("")
    status.should.have.key("TimeLoggingStopped").equal("")
    status.shouldnt.have.key("StartLoggingTime")


@mock_cloudtrail
@mock_s3
def test_get_trail_status_after_starting():
    client = boto3.client("cloudtrail", region_name="eu-west-3")
    _, _, trail_name = create_trail_simple(region_name="eu-west-3")

    client.start_logging(Name=trail_name)

    status = client.get_trail_status(Name=trail_name)
    status.should.have.key("IsLogging").equal(True)
    status.should.have.key("LatestDeliveryTime").be.a(datetime)
    status.should.have.key("StartLoggingTime").be.a(datetime)
    status.should.have.key(
        "LatestDeliveryAttemptTime"
    )  # .equal("2021-10-13T15:36:53Z")
    status.should.have.key("LatestNotificationAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptSucceeded").equal("")
    status.should.have.key(
        "LatestDeliveryAttemptSucceeded"
    )  # .equal("2021-10-13T15:36:53Z")
    status.should.have.key("TimeLoggingStarted")  # .equal("2021-10-13T15:02:21Z")
    status.should.have.key("TimeLoggingStopped").equal("")
    status.shouldnt.have.key("StopLoggingTime")


@mock_cloudtrail
@mock_s3
def test_get_trail_status_after_starting_and_stopping():
    client = boto3.client("cloudtrail", region_name="eu-west-3")
    _, _, trail_name = create_trail_simple(region_name="eu-west-3")

    client.start_logging(Name=trail_name)

    client.stop_logging(Name=trail_name)

    status = client.get_trail_status(Name=trail_name)
    status.should.have.key("IsLogging").equal(False)
    status.should.have.key("LatestDeliveryTime").be.a(datetime)
    status.should.have.key("StartLoggingTime").be.a(datetime)
    status.should.have.key("StopLoggingTime").be.a(datetime)
    status.should.have.key(
        "LatestDeliveryAttemptTime"
    )  # .equal("2021-10-13T15:36:53Z")
    status.should.have.key("LatestNotificationAttemptTime").equal("")
    status.should.have.key("LatestNotificationAttemptSucceeded").equal("")
    status.should.have.key(
        "LatestDeliveryAttemptSucceeded"
    )  # .equal("2021-10-13T15:36:53Z")
    status.should.have.key("TimeLoggingStarted")  # .equal("2021-10-13T15:02:21Z")
    status.should.have.key("TimeLoggingStopped")  # .equal("2021-10-13T15:03:21Z")


@mock_cloudtrail
@mock_s3
@mock_sns
def test_list_trails():
    client = boto3.client("cloudtrail", region_name="eu-west-3")

    _, trail1, _ = create_trail_simple()
    _, trail2, _, _ = create_trail_advanced(region_name="ap-southeast-2")
    _, trail3, _ = create_trail_simple(region_name="eu-west-1")

    all_trails = client.list_trails()["Trails"]
    all_trails.should.have.length_of(3)

    all_trails.should.contain(
        {
            "TrailARN": trail1["TrailARN"],
            "Name": trail1["Name"],
            "HomeRegion": "us-east-1",
        }
    )
    all_trails.should.contain(
        {
            "TrailARN": trail2["TrailARN"],
            "Name": trail2["Name"],
            "HomeRegion": "ap-southeast-2",
        }
    )
    all_trails.should.contain(
        {
            "TrailARN": trail3["TrailARN"],
            "Name": trail3["Name"],
            "HomeRegion": "eu-west-1",
        }
    )


@mock_cloudtrail
@mock_s3
@mock_sns
def test_describe_trails_without_shadowtrails():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, trail1, _ = create_trail_simple()
    _, trail2, _, _ = create_trail_advanced()
    _, trail3, _ = create_trail_simple(region_name="eu-west-1")

    trails = client.describe_trails()["trailList"]
    trails.should.have.length_of(3)

    first_trail = [t for t in trails if t["Name"] == trail1["Name"]][0]
    first_trail.should.have.key("Name").equal(trail1["Name"])
    first_trail.should.have.key("S3BucketName").equal(trail1["S3BucketName"])
    first_trail.should.have.key("IncludeGlobalServiceEvents").equal(True)
    first_trail.should.have.key("IsMultiRegionTrail").equal(False)
    first_trail.should.have.key("HomeRegion").equal("us-east-1")
    first_trail.should.have.key("LogFileValidationEnabled").equal(False)
    first_trail.should.have.key("HasCustomEventSelectors").equal(False)
    first_trail.should.have.key("HasInsightSelectors").equal(False)
    first_trail.should.have.key("IsOrganizationTrail").equal(False)
    first_trail.shouldnt.have.key("S3KeyPrefix")
    first_trail.shouldnt.have.key("SnsTopicName")
    first_trail.shouldnt.have.key("SnsTopicARN")

    second_trail = [t for t in trails if t["Name"] == trail2["Name"]][0]
    second_trail.should.have.key("Name").equal(trail2["Name"])
    second_trail.should.have.key("S3BucketName").equal(trail2["S3BucketName"])
    second_trail.should.have.key("S3KeyPrefix").equal(trail2["S3KeyPrefix"])
    second_trail.should.have.key("SnsTopicName").equal(trail2["SnsTopicName"])
    second_trail.should.have.key("SnsTopicARN").equal(trail2["SnsTopicARN"])
    second_trail.should.have.key("IncludeGlobalServiceEvents").equal(True)
    second_trail.should.have.key("IsMultiRegionTrail").equal(True)
    second_trail.should.have.key("HomeRegion").equal("us-east-1")
    second_trail.should.have.key("LogFileValidationEnabled").equal(True)
    second_trail.should.have.key("HasCustomEventSelectors").equal(False)
    second_trail.should.have.key("HasInsightSelectors").equal(False)
    second_trail.should.have.key("IsOrganizationTrail").equal(True)

    third_trail = [t for t in trails if t["Name"] == trail3["Name"]][0]
    third_trail.should.have.key("Name").equal(trail3["Name"])
    third_trail.should.have.key("S3BucketName").equal(trail3["S3BucketName"])
    third_trail.should.have.key("IncludeGlobalServiceEvents").equal(True)
    third_trail.should.have.key("IsMultiRegionTrail").equal(False)
    third_trail.should.have.key("HomeRegion").equal("eu-west-1")
    third_trail.should.have.key("LogFileValidationEnabled").equal(False)
    third_trail.should.have.key("HasCustomEventSelectors").equal(False)
    third_trail.should.have.key("HasInsightSelectors").equal(False)
    third_trail.should.have.key("IsOrganizationTrail").equal(False)
    third_trail.shouldnt.have.key("S3KeyPrefix")
    third_trail.shouldnt.have.key("SnsTopicName")
    third_trail.shouldnt.have.key("SnsTopicARN")


@mock_cloudtrail
@mock_s3
@mock_sns
def test_describe_trails_with_shadowtrails_true():
    # Same behaviour as if shadowtrails-parameter was not supplied
    client = boto3.client("cloudtrail", region_name="us-east-1")
    create_trail_simple()
    create_trail_advanced()
    create_trail_simple(region_name="eu-west-1")

    trails = client.describe_trails(includeShadowTrails=True)["trailList"]
    trails.should.have.length_of(3)

    eu_client = boto3.client("cloudtrail", region_name="eu-west-1")
    trails = eu_client.describe_trails(includeShadowTrails=True)["trailList"]
    trails.should.have.length_of(3)


@mock_cloudtrail
@mock_s3
@mock_sns
def test_describe_trails_with_shadowtrails_false():
    # Only trails for the current region should now be returned
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name1 = create_trail_simple()
    _, _, _, name2 = create_trail_advanced()
    _, _, name3 = create_trail_simple(region_name="eu-west-1")

    trails = client.describe_trails(includeShadowTrails=False)["trailList"]
    trails.should.have.length_of(2)
    [t["Name"] for t in trails].should.equal([name1, name2])

    eu_client = boto3.client("cloudtrail", region_name="eu-west-1")
    trails = eu_client.describe_trails(includeShadowTrails=False)["trailList"]
    trails.should.have.length_of(1)
    [t["Name"] for t in trails].should.equal([name3])


@mock_cloudtrail
@mock_s3
def test_delete_trail():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name = create_trail_simple()

    trails = client.describe_trails()["trailList"]
    trails.should.have.length_of(1)

    client.delete_trail(Name=name)

    trails = client.describe_trails()["trailList"]
    trails.should.have.length_of(0)


@mock_cloudtrail
@mock_s3
def test_update_trail_simple():
    client = boto3.client("cloudtrail", region_name="ap-southeast-2")
    bucket_name, trail, name = create_trail_simple(region_name="ap-southeast-2")
    resp = client.update_trail(Name=name)
    resp.should.have.key("Name").equal(name)
    resp.should.have.key("S3BucketName").equal(bucket_name)
    resp.should.have.key("IncludeGlobalServiceEvents").equal(True)
    resp.should.have.key("IsMultiRegionTrail").equal(False)
    resp.should.have.key("LogFileValidationEnabled").equal(False)
    resp.should.have.key("IsOrganizationTrail").equal(False)
    resp.shouldnt.have.key("S3KeyPrefix")
    resp.shouldnt.have.key("SnsTopicName")
    resp.shouldnt.have.key("SnsTopicARN")

    trail = client.get_trail(Name=name)["Trail"]
    trail.should.have.key("Name").equal(name)
    trail.should.have.key("S3BucketName").equal(bucket_name)
    trail.should.have.key("IncludeGlobalServiceEvents").equal(True)
    trail.should.have.key("IsMultiRegionTrail").equal(False)
    trail.should.have.key("LogFileValidationEnabled").equal(False)
    trail.should.have.key("IsOrganizationTrail").equal(False)
    trail.shouldnt.have.key("S3KeyPrefix")
    trail.shouldnt.have.key("SnsTopicName")
    trail.shouldnt.have.key("SnsTopicARN")


@mock_cloudtrail
@mock_s3
def test_update_trail_full():
    client = boto3.client("cloudtrail", region_name="ap-southeast-1")
    _, trail, name = create_trail_simple(region_name="ap-southeast-1")
    resp = client.update_trail(
        Name=name,
        S3BucketName="updated_bucket",
        S3KeyPrefix="s3kp",
        SnsTopicName="stn",
        IncludeGlobalServiceEvents=False,
        IsMultiRegionTrail=True,
        EnableLogFileValidation=True,
        CloudWatchLogsLogGroupArn="cwllga",
        CloudWatchLogsRoleArn="cwlra",
        KmsKeyId="kki",
        IsOrganizationTrail=True,
    )
    resp.should.have.key("Name").equal(name)
    resp.should.have.key("S3BucketName").equal("updated_bucket")
    resp.should.have.key("S3KeyPrefix").equals("s3kp")
    resp.should.have.key("SnsTopicName").equals("stn")
    resp.should.have.key("IncludeGlobalServiceEvents").equal(False)
    resp.should.have.key("IsMultiRegionTrail").equal(True)
    resp.should.have.key("LogFileValidationEnabled").equal(True)
    resp.should.have.key("IsOrganizationTrail").equal(True)

    trail = client.get_trail(Name=name)["Trail"]
    trail.should.have.key("Name").equal(name)
    trail.should.have.key("S3BucketName").equal("updated_bucket")
    trail.should.have.key("S3KeyPrefix").equals("s3kp")
    trail.should.have.key("SnsTopicName").equals("stn")
    trail.should.have.key("IncludeGlobalServiceEvents").equal(False)
    trail.should.have.key("IsMultiRegionTrail").equal(True)
    trail.should.have.key("LogFileValidationEnabled").equal(True)
    trail.should.have.key("IsOrganizationTrail").equal(True)
    trail.should.have.key("CloudWatchLogsLogGroupArn").equals("cwllga")
    trail.should.have.key("CloudWatchLogsRoleArn").equals("cwlra")
    trail.should.have.key("KmsKeyId").equals("kki")
