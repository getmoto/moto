import json

import boto3

from moto import mock_aws, server
from moto.utilities.constants import APPLICATION_AMZ_JSON_1_1
from tests import DEFAULT_ACCOUNT_ID as ACCOUNT_ID


def _post(test_client, target, body):
    headers = {
        "X-Amz-Target": f"CodeBuild_20161006.{target}",
        "Content-Type": APPLICATION_AMZ_JSON_1_1,
        # The Authorization header is how the server learns the region.
        "Authorization": (
            "AWS4-HMAC-SHA256 Credential=test/20260911/eu-west-1/codebuild/aws4_request, "
            "SignedHeaders=host;x-amz-target, Signature=0"
        ),
    }
    res = test_client.post("/", headers=headers, data=json.dumps(body))
    return json.loads(res.data.decode("utf-8"))


def _assert_epoch(build):
    # CodeBuild's JSON protocol declares startTime/endTime as `timestamp`, which on the wire is epoch seconds.
    # botocore happens to parse ISO strings too, but the AWS SDK for JavaScript v3 (expectNumber) and Go v2 do not,
    # so a string here breaks clients that pass boto3-based tests.
    assert isinstance(build["startTime"], (int, float)), build["startTime"]
    if "endTime" in build:
        assert isinstance(build["endTime"], (int, float)), build["endTime"]
        assert build["endTime"] >= build["startTime"]
    for phase in build["phases"]:
        for key in ("startTime", "endTime"):
            if key in phase:
                assert isinstance(phase[key], (int, float)), (phase["phaseType"], key)


@mock_aws
def test_build_timestamps_are_epoch_seconds_on_the_wire():
    client = boto3.client("codebuild", region_name="eu-west-1")
    client.create_project(
        name="my_project",
        source={"type": "S3", "location": "bucketname/path/file.zip"},
        artifacts={"type": "NO_ARTIFACTS"},
        environment={
            "type": "LINUX_CONTAINER",
            "image": "contents_not_validated",
            "computeType": "BUILD_GENERAL1_SMALL",
        },
        serviceRole=f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/my-codebuild-service-role",
    )

    test_client = server.create_backend_app("codebuild").test_client()

    started = _post(test_client, "StartBuild", {"projectName": "my_project"})["build"]
    _assert_epoch(started)

    fetched = _post(test_client, "BatchGetBuilds", {"ids": [started["id"]]})["builds"][
        0
    ]
    _assert_epoch(fetched)
    assert fetched["currentPhase"] == "COMPLETED"

    stopped = _post(test_client, "StopBuild", {"id": started["id"]})["build"]
    _assert_epoch(stopped)
