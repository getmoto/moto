import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_robot_application():
    client = boto3.client("robomaker", region_name="eu-west-1")
    app = client.create_robot_application(
        name="viki",
        sources=[{"s3Bucket": "sth", "s3Key": "else"}],
        robotSoftwareSuite={"name": "ROS", "version": "Kinetic"},
    )
    assert "robot-application/viki" in app["arn"]
    assert app["name"] == "viki"
    assert app["sources"] == [{"s3Bucket": "sth", "s3Key": "else"}]
    assert app["robotSoftwareSuite"] == {"name": "ROS", "version": "Kinetic"}

    app = client.describe_robot_application(application="viki")
    assert "robot-application/viki" in app["arn"]
    assert app["name"] == "viki"
    assert app["sources"] == [{"s3Bucket": "sth", "s3Key": "else"}]
    assert app["robotSoftwareSuite"] == {"name": "ROS", "version": "Kinetic"}

    apps = client.list_robot_applications()["robotApplicationSummaries"]
    assert len(apps) == 1
    assert apps[0]["name"] == "viki"

    client.delete_robot_application(application="viki")

    apps = client.list_robot_applications()["robotApplicationSummaries"]
    assert len(apps) == 0
