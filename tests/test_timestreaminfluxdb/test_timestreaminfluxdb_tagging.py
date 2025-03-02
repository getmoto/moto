import boto3

from moto import mock_aws


@mock_aws
def test_list_tags_for_db_instance():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
        tags={"key1": "value1", "key2": "value2"},
    )

    arn = response["arn"]
    response = client.list_tags_for_resource(resourceArn=arn)
    assert response["tags"] == {"key1": "value1", "key2": "value2"}


@mock_aws
def test_tag_resources():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
        tags={"key1": "value1", "key2": "value2"},
    )

    arn = response["arn"]

    # add a tag
    additional_tags = {"key3": "value3"}
    response = client.tag_resource(resourceArn=arn, tags=additional_tags)

    response = client.list_tags_for_resource(resourceArn=arn)
    assert response["tags"] == {"key1": "value1", "key2": "value2", "key3": "value3"}


@mock_aws
def test_untag_resources():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
        tags={"key1": "value1", "key2": "value2"},
    )

    arn = response["arn"]

    # remove tags
    response = client.untag_resource(resourceArn=arn, tagKeys=["key1"])

    response = client.list_tags_for_resource(resourceArn=arn)
    assert response["tags"] == {"key2": "value2"}
