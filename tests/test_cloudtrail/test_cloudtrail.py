from datetime import datetime
from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


@mock_aws
def test_create_trail_without_bucket():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name="mytrailname", S3BucketName="specificweirdbucketthatdoesnotexist"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "S3BucketDoesNotExistException"
    assert (
        err["Message"]
        == "S3 bucket specificweirdbucketthatdoesnotexist does not exist!"
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
@mock_aws
def test_create_trail_invalid_name(name, message):
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_trail(
            Name=name, S3BucketName="specificweirdbucketthatdoesnotexist"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidTrailNameException"
    assert err["Message"] == message


@mock_aws
def test_create_trail_simple():
    bucket_name, resp, trail_name = create_trail_simple()
    assert resp["Name"] == trail_name
    assert resp["S3BucketName"] == bucket_name
    assert "S3KeyPrefix" not in resp
    assert "SnsTopicName" not in resp
    assert "SnsTopicARN" not in resp
    assert resp["IncludeGlobalServiceEvents"] is True
    assert resp["IsMultiRegionTrail"] is False
    assert (
        resp["TrailARN"]
        == f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{trail_name}"
    )
    assert resp["LogFileValidationEnabled"] is False
    assert resp["IsOrganizationTrail"] is False


def create_trail_simple(region_name="us-east-1"):
    client = boto3.client("cloudtrail", region_name=region_name)
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = str(uuid4())
    s3.create_bucket(Bucket=bucket_name)
    trail_name = str(uuid4())
    resp = client.create_trail(Name=trail_name, S3BucketName=bucket_name)
    return bucket_name, resp, trail_name


@mock_aws
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
    assert err["Code"] == "InvalidParameterCombinationException"
    # Note that this validation occurs before the S3 bucket is validated
    assert err["Message"] == "Multi-Region trail must include global service events."


@mock_aws
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
    assert err["Code"] == "InsufficientSnsTopicPolicyException"
    assert (
        err["Message"] == "SNS Topic does not exist or the topic policy is incorrect!"
    )


@mock_aws
def test_create_trail_advanced():
    bucket_name, resp, sns_topic_name, trail_name = create_trail_advanced()
    assert resp["Name"] == trail_name
    assert resp["S3BucketName"] == bucket_name
    assert resp["S3KeyPrefix"] == "s3kp"
    assert resp["SnsTopicName"] == sns_topic_name
    assert resp["SnsTopicARN"] == f"arn:aws:sns:us-east-1:{ACCOUNT_ID}:{sns_topic_name}"
    assert resp["IncludeGlobalServiceEvents"] is True
    assert resp["IsMultiRegionTrail"] is True
    assert (
        resp["TrailARN"]
        == f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{trail_name}"
    )
    assert resp["LogFileValidationEnabled"] is True
    assert resp["IsOrganizationTrail"] is True
    assert resp["CloudWatchLogsLogGroupArn"] == "cwllga"
    assert resp["CloudWatchLogsRoleArn"] == "cwlra"
    assert resp["KmsKeyId"] == "kki"


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


@mock_aws
def test_get_trail_with_one_char():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail(Name="?")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidTrailNameException"
    assert (
        err["Message"]
        == "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 1 characters."
    )


@mock_aws
def test_get_trail_unknown():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail(Name="unknowntrail")
    err = exc.value.response["Error"]
    assert err["Code"] == "TrailNotFoundException"
    assert err["Message"] == f"Unknown trail: unknowntrail for the user: {ACCOUNT_ID}"


@mock_aws
def test_get_trail():
    create_trail_simple()
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name = create_trail_simple()
    trail = client.get_trail(Name=name)["Trail"]
    assert trail["Name"] == name
    assert trail["IncludeGlobalServiceEvents"] is True
    assert trail["IsMultiRegionTrail"] is False
    assert (
        trail["TrailARN"] == f"arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/{name}"
    )


@mock_aws
def test_get_trail_status_with_one_char():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail_status(Name="?")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidTrailNameException"
    assert (
        err["Message"]
        == "Trail name too short. Minimum allowed length: 3 characters. Specified name length: 1 characters."
    )


@mock_aws
def test_get_trail_status_unknown_trail():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.get_trail_status(Name="unknowntrail")
    err = exc.value.response["Error"]
    assert err["Code"] == "TrailNotFoundException"
    assert (
        err["Message"]
        == f"Unknown trail: arn:aws:cloudtrail:us-east-1:{ACCOUNT_ID}:trail/unknowntrail for the user: {ACCOUNT_ID}"
    )


@mock_aws
def test_get_trail_status_inactive():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, trail_name = create_trail_simple()
    status = client.get_trail_status(Name=trail_name)
    assert status["IsLogging"] is False
    assert status["LatestDeliveryAttemptTime"] == ""
    assert status["LatestNotificationAttemptTime"] == ""
    assert status["LatestNotificationAttemptSucceeded"] == ""
    assert status["LatestDeliveryAttemptSucceeded"] == ""
    assert status["TimeLoggingStarted"] == ""
    assert status["TimeLoggingStopped"] == ""
    assert "StartLoggingTime" not in status


@mock_aws
def test_get_trail_status_arn_inactive():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, resp, _ = create_trail_simple()
    status = client.get_trail_status(Name=resp["TrailARN"])
    assert status["IsLogging"] is False
    assert status["LatestDeliveryAttemptTime"] == ""
    assert status["LatestNotificationAttemptTime"] == ""
    assert status["LatestNotificationAttemptSucceeded"] == ""
    assert status["LatestDeliveryAttemptSucceeded"] == ""
    assert status["TimeLoggingStarted"] == ""
    assert status["TimeLoggingStopped"] == ""
    assert "StartLoggingTime" not in status


@mock_aws
def test_get_trail_status_after_starting():
    client = boto3.client("cloudtrail", region_name="eu-west-3")
    _, _, trail_name = create_trail_simple(region_name="eu-west-3")

    client.start_logging(Name=trail_name)

    status = client.get_trail_status(Name=trail_name)
    assert status["IsLogging"] is True
    assert isinstance(status["LatestDeliveryTime"], datetime)
    assert isinstance(status["StartLoggingTime"], datetime)
    # .equal("2021-10-13T15:36:53Z")
    assert "LatestDeliveryAttemptTime" in status
    assert status["LatestNotificationAttemptTime"] == ""
    assert status["LatestNotificationAttemptSucceeded"] == ""
    # .equal("2021-10-13T15:36:53Z")
    assert "LatestDeliveryAttemptSucceeded" in status
    assert "TimeLoggingStarted" in status  # .equal("2021-10-13T15:02:21Z")
    assert status["TimeLoggingStopped"] == ""
    assert "StopLoggingTime" not in status


@mock_aws
def test_get_trail_status_after_starting_and_stopping():
    client = boto3.client("cloudtrail", region_name="eu-west-3")
    _, _, trail_name = create_trail_simple(region_name="eu-west-3")

    client.start_logging(Name=trail_name)

    client.stop_logging(Name=trail_name)

    status = client.get_trail_status(Name=trail_name)
    assert status["IsLogging"] is False
    assert isinstance(status["LatestDeliveryTime"], datetime)
    assert isinstance(status["StartLoggingTime"], datetime)
    assert isinstance(status["StopLoggingTime"], datetime)
    # .equal("2021-10-13T15:36:53Z")
    assert "LatestDeliveryAttemptTime" in status
    assert status["LatestNotificationAttemptTime"] == ""
    assert status["LatestNotificationAttemptSucceeded"] == ""
    # .equal("2021-10-13T15:36:53Z")
    assert "LatestDeliveryAttemptSucceeded" in status
    assert "TimeLoggingStarted" in status  # .equal("2021-10-13T15:02:21Z")
    assert "TimeLoggingStopped" in status  # .equal("2021-10-13T15:03:21Z")


@mock_aws
def test_get_trail_status_multi_region_not_from_the_home_region():
    # CloudTrail client
    client_us_east_1 = boto3.client("cloudtrail", region_name="us-east-1")

    # Create Trail
    _, _, _, trail_name_us_east_1 = create_trail_advanced()

    # Start Logging
    _ = client_us_east_1.start_logging(Name=trail_name_us_east_1)

    # Check Trails in the Home Region us-east-1
    trails_us_east_1 = client_us_east_1.describe_trails()["trailList"]
    trail_arn_us_east_1 = trails_us_east_1[0]["TrailARN"]
    assert len(trails_us_east_1) == 1

    # Get Trail status in the Home Region us-east-1
    trail_status_us_east_1 = client_us_east_1.get_trail_status(Name=trail_arn_us_east_1)
    assert trail_status_us_east_1["IsLogging"]

    # Check Trails in another region eu-west-1 for a MultiRegion trail
    client_eu_west_1 = boto3.client("cloudtrail", region_name="eu-west-1")
    trails_eu_west_1 = client_eu_west_1.describe_trails()["trailList"]
    assert len(trails_eu_west_1) == 1

    # Get Trail status in another region eu-west-1 for a MultiRegion trail
    trail_status_us_east_1 = client_eu_west_1.get_trail_status(Name=trail_arn_us_east_1)
    assert trail_status_us_east_1["IsLogging"]


@mock_aws
def test_list_trails_different_home_region_one_multiregion():
    client = boto3.client("cloudtrail", region_name="eu-west-3")

    create_trail_simple()
    _, trail2, _, _ = create_trail_advanced(region_name="ap-southeast-2")
    create_trail_simple(region_name="eu-west-1")

    all_trails = client.list_trails()["Trails"]

    # Only the Trail created in the ap-southeast-2 is MultiRegion
    assert all_trails == [
        {
            "TrailARN": trail2["TrailARN"],
            "Name": trail2["Name"],
            "HomeRegion": "ap-southeast-2",
        }
    ]


@mock_aws
def test_list_trails_different_home_region_no_multiregion():
    client = boto3.client("cloudtrail", region_name="eu-west-3")

    create_trail_simple()
    create_trail_simple(region_name="ap-southeast-2")
    create_trail_simple(region_name="eu-west-1")

    all_trails = client.list_trails()["Trails"]
    # Since there is no MultiRegion Trail created
    # the eu-west-3 has no Trails
    assert len(all_trails) == 0


@mock_aws
def test_describe_trails_without_shadowtrails():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, trail1, _ = create_trail_simple()
    _, trail2, _, _ = create_trail_advanced()
    create_trail_simple(region_name="eu-west-1")

    # There are two Trails created in the us-east-1
    # one MultiRegion and the other is not MultiRegion
    trails = client.describe_trails()["trailList"]
    assert len(trails) == 2

    first_trail = [t for t in trails if t["Name"] == trail1["Name"]][0]
    assert first_trail["Name"] == trail1["Name"]
    assert first_trail["S3BucketName"] == trail1["S3BucketName"]
    assert first_trail["IncludeGlobalServiceEvents"] is True
    assert first_trail["IsMultiRegionTrail"] is False
    assert first_trail["HomeRegion"] == "us-east-1"
    assert first_trail["LogFileValidationEnabled"] is False
    assert first_trail["HasCustomEventSelectors"] is False
    assert first_trail["HasInsightSelectors"] is False
    assert first_trail["IsOrganizationTrail"] is False
    assert "S3KeyPrefix" not in first_trail
    assert "SnsTopicName" not in first_trail
    assert "SnsTopicARN" not in first_trail

    second_trail = [t for t in trails if t["Name"] == trail2["Name"]][0]
    assert second_trail["Name"] == trail2["Name"]
    assert second_trail["S3BucketName"] == trail2["S3BucketName"]
    assert second_trail["S3KeyPrefix"] == trail2["S3KeyPrefix"]
    assert second_trail["SnsTopicName"] == trail2["SnsTopicName"]
    assert second_trail["SnsTopicARN"] == trail2["SnsTopicARN"]
    assert second_trail["IncludeGlobalServiceEvents"] is True
    assert second_trail["IsMultiRegionTrail"] is True
    assert second_trail["HomeRegion"] == "us-east-1"
    assert second_trail["LogFileValidationEnabled"] is True
    assert second_trail["HasCustomEventSelectors"] is False
    assert second_trail["HasInsightSelectors"] is False
    assert second_trail["IsOrganizationTrail"] is True


@mock_aws
def test_describe_trails_with_shadowtrails_true():
    # Same behaviour as if shadowtrails-parameter was not supplied
    client = boto3.client("cloudtrail", region_name="us-east-1")
    create_trail_simple()
    create_trail_advanced()
    create_trail_simple(region_name="eu-west-1")

    # There are two Trails created in the us-east-1
    # one MultiRegion and the other is not MultiRegion
    trails = client.describe_trails(includeShadowTrails=True)["trailList"]
    assert len(trails) == 2

    # There are two Trails in the eu-west-1
    # one MultiRegion (created in the us-east-1)
    # and another not MultiRegion created in the us-east-1
    eu_client = boto3.client("cloudtrail", region_name="eu-west-1")
    trails = eu_client.describe_trails(includeShadowTrails=True)["trailList"]
    assert len(trails) == 2


@mock_aws
def test_describe_trails_with_shadowtrails_false():
    # Only trails for the current region should now be returned
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name1 = create_trail_simple()
    _, _, _, name2 = create_trail_advanced()
    _, _, name3 = create_trail_simple(region_name="eu-west-1")

    trails = client.describe_trails(includeShadowTrails=False)["trailList"]
    assert len(trails) == 2
    assert [t["Name"] for t in trails] == [name1, name2]

    eu_client = boto3.client("cloudtrail", region_name="eu-west-1")
    trails = eu_client.describe_trails(includeShadowTrails=False)["trailList"]
    assert len(trails) == 1
    assert [t["Name"] for t in trails] == [name3]


@mock_aws
def test_delete_trail():
    client = boto3.client("cloudtrail", region_name="us-east-1")
    _, _, name = create_trail_simple()

    trails = client.describe_trails()["trailList"]
    assert len(trails) == 1

    client.delete_trail(Name=name)

    trails = client.describe_trails()["trailList"]
    assert len(trails) == 0


@mock_aws
def test_update_trail_simple():
    client = boto3.client("cloudtrail", region_name="ap-southeast-2")
    bucket_name, trail, name = create_trail_simple(region_name="ap-southeast-2")
    resp = client.update_trail(Name=name)
    assert resp["Name"] == name
    assert resp["S3BucketName"] == bucket_name
    assert resp["IncludeGlobalServiceEvents"] is True
    assert resp["IsMultiRegionTrail"] is False
    assert resp["LogFileValidationEnabled"] is False
    assert resp["IsOrganizationTrail"] is False
    assert "S3KeyPrefix" not in resp
    assert "SnsTopicName" not in resp
    assert "SnsTopicARN" not in resp

    trail = client.get_trail(Name=name)["Trail"]
    assert trail["Name"] == name
    assert trail["S3BucketName"] == bucket_name
    assert trail["IncludeGlobalServiceEvents"] is True
    assert trail["IsMultiRegionTrail"] is False
    assert trail["LogFileValidationEnabled"] is False
    assert trail["IsOrganizationTrail"] is False
    assert "S3KeyPrefix" not in trail
    assert "SnsTopicName" not in trail
    assert "SnsTopicARN" not in trail


@mock_aws
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
    assert resp["Name"] == name
    assert resp["S3BucketName"] == "updated_bucket"
    assert resp["S3KeyPrefix"] == "s3kp"
    assert resp["SnsTopicName"] == "stn"
    assert resp["IncludeGlobalServiceEvents"] is False
    assert resp["IsMultiRegionTrail"] is True
    assert resp["LogFileValidationEnabled"] is True
    assert resp["IsOrganizationTrail"] is True

    trail = client.get_trail(Name=name)["Trail"]
    assert trail["Name"] == name
    assert trail["S3BucketName"] == "updated_bucket"
    assert trail["S3KeyPrefix"] == "s3kp"
    assert trail["SnsTopicName"] == "stn"
    assert trail["IncludeGlobalServiceEvents"] is False
    assert trail["IsMultiRegionTrail"] is True
    assert trail["LogFileValidationEnabled"] is True
    assert trail["IsOrganizationTrail"] is True
    assert trail["CloudWatchLogsLogGroupArn"] == "cwllga"
    assert trail["CloudWatchLogsRoleArn"] == "cwlra"
    assert trail["KmsKeyId"] == "kki"
