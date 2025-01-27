"""Unit tests for timestreaminfluxdb-supported APIs."""

import boto3

from moto import mock_aws

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


"""Unit tests for timestreaminfluxdb-supported APIs."""


@mock_aws
def test_create_db_instance_success():
    client = boto3.client("timestream-influxdb", region_name="us-east-1")

    response = client.create_db_instance(
        name="test-instance",
        password="password123",
        dbInstanceType="db.influx.medium",
        vpcSubnetIds=["subnet-0123456789abcdef0"],
        vpcSecurityGroupIds=["sg-0123456789abcdef0"],
        allocatedStorage=123,
    )
    # assert response["allocatedStorage"] == 123
    # assert response["dbInstanceType"] == "db.influx.medium"
    # assert response["name"] == "test-instance"
    # assert response["vpcSecurityGroupIds"] == ["sg-0123456789abcdef0"]
    # assert response["vpcSubnetIds"] == ["subnet-0123456789abcdef0"]

    # assert "arn" in response
    # assert "availabilityZone" in response
    # assert "dbParameterGroupIdentifier" in response
    # assert "dbStorageType" in response
    # assert "deploymentType" in response
    # assert "endpoint" in response
    # assert "id" in response
    # assert "influxAuthParametersSecretArn" in response
    # assert "networkType" in response
    # assert "port" in response
    # assert "publiclyAccessible" in response
    # assert "secondaryAvailabilityZone" in response
    # assert "status" in response
    # assert "vpcSecurityGroupIds" in response
    # assert "vpcSubnetIds" in response
    # assert "logDeliveryConfiguration" in response


@mock_aws
def test_create_db_instance_duplicate_identifier():
    client = boto3.client("timestream-influxdb", region_name="ap-southeast-1")


#     response = client.create_db_instance(
#         name="test-instance",
#         password="password123",
#         dbInstanceType="db.influx.medium",
#         vpcSubnetIds=["subnet-0123456789abcdef0"],
#         vpcSecurityGroupIds=["sg-0123456789abcdef0"],
#         allocatedStorage=123,
#     )

#     with pytest.raises(ClientError) as exc:
#         client.create_db_instance(
#             name="test-instance",
#             password="password123",
#             dbInstanceType="db.influx.medium",
#             vpcSubnetIds=["subnet-0123456789abcdef0"],
#             vpcSecurityGroupIds=["sg-0123456789abcdef0"],
#             allocatedStorage=123,
#         )

#     assert exc.value.response["Error"]["Code"] == "DBInstanceAlreadyExists"


# @mock_aws
# def test_create_db_instance_name_invalid():
#     invalid_names = [
#         "1muststartwithletter",
#         "cantendwithhyphen_",
#         "nodoublehyphen--",
#     ]
#     client = boto3.client("timestream-influxdb", region_name="us-east-1")

#     for invalid_name in invalid_names:
#         with pytest.raises(ClientError) as exc:
#             client.create_db_instance(
#                 name=invalid_name,
#                 password="password123",
#                 dbInstanceType="db.influx.medium",
#                 vpcSubnetIds=["subnet-0123456789abcdef0"],
#                 vpcSecurityGroupIds=["sg-0123456789abcdef0"],
#                 allocatedStorage=123,
#             )
#         assert exc.value.response["Error"]["Code"] == "ValidationException"
