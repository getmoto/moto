"""Unit tests for osis-supported APIs."""

import json

import boto3
import pytest
import requests
from botocore.exceptions import ClientError

from moto import mock_aws, settings
from moto.moto_api import state_manager

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

BASIC_PIPELINE_KWARGS = {
    "PipelineName": "test",
    "MinUnits": 2,
    "MaxUnits": 4,
    "PipelineConfigurationBody": """version: "2"\nopensearch-migration-pipeline:\n  source:
        \n    opensearch:\n      acknowledgments: true
        \n      hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:
        \n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n        serverless: false\n  sink:\n    - opensearch:
        \n        hosts: ["https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com"]
        \n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n          region: "eu-west-1"\n          serverless: true\n""",
}


@mock_aws
def test_create_pipeline():
    set_transition()
    client = boto3.client("osis", region_name="eu-west-1")
    resp = client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    assert resp["PipelineName"] == "test"
    assert resp["PipelineArn"] == "arn:aws:osis:eu-west-1:123456789012:pipeline/test"
    assert resp["MinUnits"] == 2
    assert resp["MaxUnits"] == 4
    assert resp["Status"] == "ACTIVE"
    assert (
        resp["StatusReason"]["Description"] == "The pipeline is ready to ingest data."
    )
    assert (
        resp["PipelineConfigurationBody"]
        == BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"]
    )
    assert (
        ".eu-west-1.osis.amazonaws.com" in resp["IngestEndpointUrls"][0]
        and "test" in resp["IngestEndpointUrls"][0]
    )
    assert resp["ServiceVpcEndpoints"][0]["ServiceName"] == "OPENSEARCH_SERVERLESS"
    assert resp["Destinations"][0]["ServiceName"] == "OpenSearch_Serverless"
    assert (
        resp["Destinations"][0]["Endpoint"]
        == "https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com"
    )
    assert "VpcEndpointService" not in resp
    assert "VpcOptions" not in resp
    assert resp["Tags"] == []

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")
    sg = ec2.create_security_group(
        GroupName="test-group", Description="Test security group sg01"
    )

    kwargs = {
        "PipelineName": "test-2",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": """log-pipeline:\n  processor:\n  - date:
        \n      destination: \'@timestamp\'\n      from_time_received: true\n  - delete_entries:
        \n      with_keys:\n      - s3\n  sink:\n  - opensearch:\n      aws:
        \n        region: eu-west-1\n        serverless: true
        \n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole\n      hosts:
        \n      - https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com
        \n      index: uncompressed_logs\n  - opensearch:\n      aws:\n        region: eu-west-1
        \n        serverless: false\n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole
        \n      hosts:
        \n      - https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com
        \n      index: uncompressed_logs\n      dlq:\n        s3:\n          bucket: "dlq-bucket"
        \n          region: "eu-west-1"
        \n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"\n  - s3:\n      aws:
        \n        region: eu-west-1\n        serverless: false
        \n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole
        \n      bucket: test-s3-bucket-2\n      threshold: 3\n      codec: json\n  - s3:
        \n      aws:\n        region: eu-west-1\n        serverless: false
        \n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole
        \n      bucket: test-s3-bucket-1\n      threshold: 3\n      codec: json\n  source:
        \n    s3:\n      acknowledgments: true\n      aws:\n        region: eu-west-1
        \n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole\n      codec:
        \n        newline: null\n      compression: none\n      scan:\n        buckets:
        \n        - bucket:\n            name: test-s3-bucket-2\nlog-pipeline-2:\n  processor:
        \n  - date:\n      destination: \'@timestamp\'\n      from_time_received: true
        \n  - delete_entries:\n      with_keys:\n      - s3\n  sink:\n  - pipeline:
        \n      name: "log-to-metrics-pipeline"\n  - opensearch:\n      aws:
        \n        region: eu-west-1\n        serverless: false
        \n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole\n      hosts:
        \n      - https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com
        \n      index: uncompressed_logs\n  - s3:\n      aws:\n        region: eu-west-1
        \n        serverless: false\n        sts_role_arn: arn:aws:iam::123456789012:role/MyRole
        \n      bucket: test-s3-bucket-1\n      threshold: 3\n      codec: json\n  source:
        \n    pipeline:\n      name: "apache-log-pipeline-with-metrics"\nversion: \'2\'""",
        "LogPublishingOptions": {
            "IsLoggingEnabled": True,
            "CloudWatchLogDestination": {
                "LogGroup": "/aws/osis/test",
            },
        },
        "VpcOptions": {
            "SubnetIds": [subnet.id],
            "SecurityGroupIds": [sg.id],
            "VpcEndpointManagement": "SERVICE",
            "VpcAttachmentOptions": {
                "AttachToVpc": True,
                "CidrBlock": "172.168.1.1",
            },
        },
        "BufferOptions": {
            "PersistentBufferEnabled": True,
        },
        "EncryptionAtRestOptions": {
            "KmsKeyArn": "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        },
        "Tags": [
            {
                "Key": "TestKey",
                "Value": "TestValue",
            }
        ],
    }
    resp = client.create_pipeline(**kwargs)["Pipeline"]
    assert resp["PipelineName"] == "test-2"
    assert "CreatedAt" in resp
    assert "LastUpdatedAt" in resp
    assert resp["LogPublishingOptions"]["IsLoggingEnabled"]
    assert (
        resp["LogPublishingOptions"]["CloudWatchLogDestination"]["LogGroup"]
        == "/aws/osis/test"
    )
    assert resp["VpcEndpoints"][0]["VpcOptions"]["SubnetIds"] == [subnet.id]
    assert resp["VpcEndpoints"][0]["VpcOptions"]["SecurityGroupIds"] == [sg.id]
    assert resp["VpcEndpoints"][0]["VpcOptions"]["VpcEndpointManagement"] == "SERVICE"
    assert resp["VpcEndpoints"][0]["VpcOptions"]["VpcAttachmentOptions"]["AttachToVpc"]
    assert (
        resp["VpcEndpoints"][0]["VpcOptions"]["VpcAttachmentOptions"]["CidrBlock"]
        == "172.168.1.1"
    )
    assert (
        resp["VpcEndpoints"][0]["VpcEndpointId"]
        and resp["VpcEndpoints"][0]["VpcId"] == vpc.id
    )
    assert resp["BufferOptions"]["PersistentBufferEnabled"]
    assert (
        resp["EncryptionAtRestOptions"]["KmsKeyArn"]
        == "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    )
    assert "VpcEndpointService" not in resp
    assert resp["ServiceVpcEndpoints"][0]["ServiceName"] == "OPENSEARCH_SERVERLESS"
    assert resp["Destinations"] == [
        {
            "ServiceName": "OpenSearch_Serverless",
            "Endpoint": "https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com",
        },
        {
            "ServiceName": "OpenSearch",
            "Endpoint": "https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com",
        },
        {"ServiceName": "S3", "Endpoint": "test-s3-bucket-2"},
        {"ServiceName": "S3", "Endpoint": "test-s3-bucket-1"},
        {
            "ServiceName": "OpenSearch",
            "Endpoint": "https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com",
        },
        {"ServiceName": "S3", "Endpoint": "test-s3-bucket-1"},
    ]

    assert (
        resp["Tags"][0]["Key"] == "TestKey" and resp["Tags"][0]["Value"] == "TestValue"
    )

    assert (
        boto3.client("ec2", region_name="eu-west-1").describe_vpc_endpoints(
            VpcEndpointIds=[resp["VpcEndpoints"][0]["VpcEndpointId"]]
        )["VpcEndpoints"]
        != []
    )


@mock_aws
def test_create_pipeline_customer_endpoint():
    set_transition({"progression": "manual", "times": 1})
    client = boto3.client("osis", region_name="eu-west-1")
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")
    sg = ec2.create_security_group(
        GroupName="test-group", Description="Test security group sg01"
    )
    kwargs = {
        "PipelineName": "test",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": """version: "2"\nopensearch-migration-pipeline:\n  source:
        \n    opensearch:\n      acknowledgments: true
        \n      hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:
        \n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n        serverless: false\n  sink:\n    - opensearch:
        \n        hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n          region: "eu-west-1"\n          serverless: false\n""",
        "VpcOptions": {
            "SubnetIds": [subnet.id],
            "SecurityGroupIds": [sg.id],
            "VpcEndpointManagement": "CUSTOMER",
        },
    }
    resp = client.create_pipeline(**kwargs)["Pipeline"]
    assert resp["PipelineName"] == "test"
    assert "VpcEndpointService" in resp
    assert "ServiceVpcEndpoints" not in resp
    assert resp["VpcEndpoints"][0]["VpcOptions"]["VpcEndpointManagement"] == "CUSTOMER"
    assert "VpcEndpointId" not in resp["VpcEndpoints"][0]
    assert "VpcAttachmentOptions" not in resp["VpcEndpoints"][0]
    assert resp["Status"] == "CREATING"


@mock_aws
def test_create_pipeline_error():
    set_transition()
    client = boto3.client("osis", region_name="eu-west-1")
    kwargs = {
        "PipelineName": "test",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"],
    }
    client.create_pipeline(**kwargs)["Pipeline"]
    with pytest.raises(ClientError) as exc:
        client.create_pipeline(**kwargs)
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceAlreadyExistsException"

    kwargs["PipelineName"] = "test-2"
    kwargs["VpcOptions"] = {}
    kwargs["VpcOptions"]["SubnetIds"] = ["subnet-12345678901234567"]

    with pytest.raises(ClientError) as exc:
        client.create_pipeline(**kwargs)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid VpcOptions: The subnet ID subnet-12345678901234567 does not exist"
    )

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")

    kwargs["VpcOptions"]["SubnetIds"] = [subnet.id]
    kwargs["VpcOptions"]["SecurityGroupIds"] = ["sg-12345678901234567"]

    with pytest.raises(ClientError) as exc:
        client.create_pipeline(**kwargs)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid VpcOptions: The security group sg-12345678901234567 does not exist"
    )

    kwargs["VpcOptions"].pop("SecurityGroupIds")
    vpc = ec2.create_vpc(CidrBlock="172.29.7.0/24")
    subnet_2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.29.7.192/26")
    kwargs["VpcOptions"]["SubnetIds"].append(subnet_2.id)

    with pytest.raises(ClientError) as exc:
        client.create_pipeline(**kwargs)
    err = exc.value.response["Error"]
    assert err["Code"] == "ValidationException"
    assert (
        err["Message"]
        == "Invalid VpcOptions: All specified subnets must belong to the same VPC."
    )


@mock_aws
def test_update_pipeline():
    set_transition()
    client = boto3.client("osis", region_name="eu-west-1")
    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")
    sg = ec2.create_security_group(
        GroupName="test-group", Description="Test security group sg01"
    )

    kwargs = {
        "PipelineName": "test",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"],
        "LogPublishingOptions": {
            "IsLoggingEnabled": True,
            "CloudWatchLogDestination": {
                "LogGroup": "/aws/osis/test",
            },
        },
        "VpcOptions": {
            "SubnetIds": [subnet.id],
            "SecurityGroupIds": [sg.id],
            "VpcEndpointManagement": "SERVICE",
            "VpcAttachmentOptions": {
                "AttachToVpc": True,
                "CidrBlock": "172.168.1.1",
            },
        },
        "BufferOptions": {
            "PersistentBufferEnabled": True,
        },
        "EncryptionAtRestOptions": {
            "KmsKeyArn": "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        },
        "Tags": [
            {
                "Key": "TestKey",
                "Value": "TestValue",
            }
        ],
    }
    original = client.create_pipeline(**kwargs)["Pipeline"]
    resp = client.update_pipeline(PipelineName="test", MinUnits=3)["Pipeline"]
    assert resp["MinUnits"] == 3
    assert resp["MaxUnits"] == original["MaxUnits"]
    assert (
        resp["PipelineConfigurationBody"]
        == BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"]
    )
    assert resp["Destinations"] == original["Destinations"]
    assert resp["ServiceVpcEndpoints"] == original["ServiceVpcEndpoints"]
    assert resp["VpcEndpoints"] == original["VpcEndpoints"]
    assert resp["Tags"] == original["Tags"]
    assert resp["LogPublishingOptions"] == original["LogPublishingOptions"]
    assert resp["BufferOptions"] == original["BufferOptions"]
    assert resp["EncryptionAtRestOptions"] == original["EncryptionAtRestOptions"]
    assert resp["Status"] == "ACTIVE"


@mock_aws
def test_update_pipeline_all_args():
    set_transition({"progression": "manual", "times": 1})
    client = boto3.client("osis", region_name="eu-west-1")
    kwargs = {
        "PipelineName": "test",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"],
        "LogPublishingOptions": {
            "IsLoggingEnabled": True,
            "CloudWatchLogDestination": {
                "LogGroup": "test/osis/logs",
            },
        },
        "BufferOptions": {
            "PersistentBufferEnabled": False,
        },
        "EncryptionAtRestOptions": {
            "KmsKeyArn": "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        },
    }

    resp = client.create_pipeline(**kwargs)["Pipeline"]
    last_updated = resp["LastUpdatedAt"]
    # state transition
    client.list_pipelines()

    new_pipeline_config = """version: "2"\nopensearch-migration-pipeline:\n  source:
        \n    opensearch:\n      acknowledgments: true
        \n      hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:
        \n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n        serverless: false\n  sink:\n    - opensearch:
        \n        hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n          region: "eu-west-1"\n          serverless: false\n"""
    new_key = (
        "arn:aws:kms:eu-west-1:123456789012:key/87654321-4321-4321-4321-210987654321"
    )
    kwargs["MinUnits"] = 3
    kwargs["MaxUnits"] = 5
    kwargs["PipelineConfigurationBody"] = new_pipeline_config
    kwargs["LogPublishingOptions"]["IsLoggingEnabled"] = False
    kwargs["BufferOptions"]["PersistentBufferEnabled"] = True
    kwargs["EncryptionAtRestOptions"]["KmsKeyArn"] = new_key

    resp = client.update_pipeline(**kwargs)["Pipeline"]

    assert resp["MinUnits"] == 3
    assert resp["MaxUnits"] == 5
    assert resp["PipelineConfigurationBody"] == new_pipeline_config
    assert not resp["LogPublishingOptions"]["IsLoggingEnabled"]
    assert resp["BufferOptions"]["PersistentBufferEnabled"]
    assert resp["EncryptionAtRestOptions"]["KmsKeyArn"] == new_key
    assert resp["Destinations"][0]["ServiceName"] == "OpenSearch"
    assert (
        resp["Destinations"][0]["Endpoint"]
        == "https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"
    )
    assert "ServiceVpcEndpoints" not in resp
    assert resp["LastUpdatedAt"] > last_updated
    assert resp["Status"] == "UPDATING"


@mock_aws
def test_update_pipeline_error():
    set_transition({"progression": "manual", "times": 1})
    client = boto3.client("osis", region_name="eu-west-1")
    client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    with pytest.raises(ClientError) as exc:
        client.update_pipeline(PipelineName="test", MinUnits=3)["Pipeline"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == "Only pipelines with one of the following statuses are eligible for updates: ['UPDATE_FAILED', 'ACTIVE', 'START_FAILED', 'STOPPED']. The current status is CREATING."
    )

    with pytest.raises(ClientError) as exc:
        client.update_pipeline(PipelineName="test-2", MinUnits=3)["Pipeline"]
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Pipeline test-2 could not be found."


@mock_aws
def test_delete_pipeline():
    set_transition({"progression": "manual", "times": 2})
    client = boto3.client("osis", region_name="eu-west-1")
    original = client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    for _ in range(2):
        client.list_pipelines()
    client.delete_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    pipeline = client.list_pipelines()["Pipelines"][0]
    assert pipeline["PipelineName"] == BASIC_PIPELINE_KWARGS["PipelineName"]
    assert pipeline["Status"] == "DELETING"
    assert pipeline["LastUpdatedAt"] > original["LastUpdatedAt"]
    pipelines = client.list_pipelines()["Pipelines"]
    assert pipelines == []


@mock_aws
def test_delete_pipeline_error():
    set_transition({"progression": "manual", "times": 1})
    client = boto3.client("osis", region_name="eu-west-1")

    with pytest.raises(ClientError) as exc:
        client.delete_pipeline(PipelineName="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Pipeline test could not be found."

    client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    with pytest.raises(ClientError) as exc:
        client.delete_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == "Only pipelines with one of the following statuses are eligible for deletion: ['UPDATE_FAILED', 'ACTIVE', 'START_FAILED', 'STOPPED', 'CREATE_FAILED']. The current status is CREATING."
    )


@mock_aws
def test_get_pipeline():
    client = boto3.client("osis", region_name="eu-west-1")
    client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    resp = client.get_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])[
        "Pipeline"
    ]
    assert resp["PipelineName"] == BASIC_PIPELINE_KWARGS["PipelineName"]
    assert (
        resp["PipelineArn"]
        == f"arn:aws:osis:eu-west-1:123456789012:pipeline/{BASIC_PIPELINE_KWARGS['PipelineName']}"
    )
    assert resp["MinUnits"] == BASIC_PIPELINE_KWARGS["MinUnits"]
    assert resp["MaxUnits"] == BASIC_PIPELINE_KWARGS["MaxUnits"]
    assert resp["Status"] == "ACTIVE"
    assert (
        resp["StatusReason"]["Description"] == "The pipeline is ready to ingest data."
    )
    assert (
        resp["PipelineConfigurationBody"]
        == BASIC_PIPELINE_KWARGS["PipelineConfigurationBody"]
    )
    assert (
        ".eu-west-1.osis.amazonaws.com" in resp["IngestEndpointUrls"][0]
        and BASIC_PIPELINE_KWARGS["PipelineName"] in resp["IngestEndpointUrls"][0]
    )
    assert resp["ServiceVpcEndpoints"][0]["ServiceName"] == "OPENSEARCH_SERVERLESS"
    assert resp["Destinations"][0]["ServiceName"] == "OpenSearch_Serverless"
    assert (
        resp["Destinations"][0]["Endpoint"]
        == "https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com"
    )
    assert "VpcEndpointService" not in resp
    assert "VpcEndpoints" not in resp
    assert resp["Tags"] == []
    assert "CreatedAt" in resp
    assert "LastUpdatedAt" in resp
    assert "LogPublishingOptions" not in resp
    assert "BufferOptions" not in resp
    assert "EncryptionAtRestOptions" not in resp

    ec2 = boto3.resource("ec2", region_name="eu-west-1")
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24")
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="172.28.7.192/26")
    sg = ec2.create_security_group(
        GroupName="test-group", Description="Test security group sg01"
    )

    kwargs = {
        "PipelineName": "test-2",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": """version: "2"\nopensearch-migration-pipeline:\n  source:
        \n    opensearch:\n      acknowledgments: true
        \n      hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:
        \n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n        serverless: false\n  sink:\n    - opensearch:
        \n        hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
        \n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
        \n          region: "eu-west-1"\n          serverless: false\n""",
        "LogPublishingOptions": {
            "IsLoggingEnabled": True,
            "CloudWatchLogDestination": {
                "LogGroup": "/aws/osis/test",
            },
        },
        "VpcOptions": {
            "SubnetIds": [subnet.id],
            "SecurityGroupIds": [sg.id],
            "VpcEndpointManagement": "SERVICE",
            "VpcAttachmentOptions": {
                "AttachToVpc": True,
                "CidrBlock": "172.168.1.1",
            },
        },
        "BufferOptions": {
            "PersistentBufferEnabled": True,
        },
        "EncryptionAtRestOptions": {
            "KmsKeyArn": "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012",
        },
        "Tags": [
            {
                "Key": "TestKey",
                "Value": "TestValue",
            }
        ],
    }
    client.create_pipeline(**kwargs)
    resp = client.get_pipeline(PipelineName="test-2")["Pipeline"]
    assert "ServiceVpcEndpoints" not in resp
    assert resp["Destinations"][0]["ServiceName"] == "OpenSearch"
    assert (
        resp["Destinations"][0]["Endpoint"]
        == "https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"
    )
    assert "VpcEndpointService" not in resp
    assert resp["VpcEndpoints"][0]["VpcOptions"] == {
        "SubnetIds": [subnet.id],
        "SecurityGroupIds": [sg.id],
        "VpcEndpointManagement": "SERVICE",
        "VpcAttachmentOptions": {
            "AttachToVpc": True,
            "CidrBlock": "172.168.1.1",
        },
    }
    assert "VpcEndpointId" in resp["VpcEndpoints"][0]
    assert resp["VpcEndpoints"][0]["VpcId"] == vpc.id
    assert resp["Tags"] == [
        {
            "Key": "TestKey",
            "Value": "TestValue",
        }
    ]
    assert resp["LogPublishingOptions"] == {
        "IsLoggingEnabled": True,
        "CloudWatchLogDestination": {
            "LogGroup": "/aws/osis/test",
        },
    }
    assert resp["BufferOptions"]["PersistentBufferEnabled"]
    assert (
        resp["EncryptionAtRestOptions"]["KmsKeyArn"]
        == "arn:aws:kms:eu-west-1:123456789012:key/12345678-1234-1234-1234-123456789012"
    )


@mock_aws
def test_get_pipeline_error():
    client = boto3.client("osis", region_name="eu-west-1")
    with pytest.raises(ClientError) as exc:
        client.get_pipeline(PipelineName="test")
    err = exc.value.response["Error"]
    assert err["Code"] == "ResourceNotFoundException"
    assert err["Message"] == "Pipeline test could not be found."


@mock_aws
def test_list_pipelines():
    set_transition({"progression": "manual", "times": 1})
    client = boto3.client("osis", region_name="ap-southeast-1")
    resp = client.list_pipelines()
    assert resp["Pipelines"] == []
    client.create_pipeline(**BASIC_PIPELINE_KWARGS)
    resp = client.list_pipelines()["Pipelines"][0]
    assert resp["PipelineName"] == "test"
    assert (
        resp["PipelineArn"]
        == f"arn:aws:osis:ap-southeast-1:123456789012:pipeline/{BASIC_PIPELINE_KWARGS['PipelineName']}"
    )
    assert resp["MinUnits"] == 2
    assert resp["MaxUnits"] == 4
    assert resp["Status"] == "ACTIVE"
    assert (
        resp["StatusReason"]["Description"] == "The pipeline is ready to ingest data."
    )
    assert resp["Tags"] == []
    assert "CreatedAt" in resp
    assert "LastUpdatedAt" in resp

    kwargs = {
        "PipelineName": "test-2",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": """version: "2"\nopensearch-migration-pipeline:\n  source:
            \n    opensearch:\n      acknowledgments: true
            \n      hosts: ["https://vpc-test-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]
            \n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:
            \n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
            \n        serverless: false\n  sink:\n    - opensearch:
            \n        hosts: ["https://kbjahvxo2jgx8beq2vob.eu-west-1.aoss.amazonaws.com"]
            \n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"
            \n          region: "eu-west-1"\n          serverless: true\n""",
    }
    client.create_pipeline(**kwargs)
    assert len(client.list_pipelines()["Pipelines"]) == 2


@mock_aws
def test_list_tags_for_resource():
    client = boto3.client("osis", region_name="eu-west-1")
    resp = client.create_pipeline(
        **BASIC_PIPELINE_KWARGS, Tags=[{"Key": "TestKey", "Value": "TestValue"}]
    )["Pipeline"]
    tags = client.list_tags_for_resource(Arn=resp["PipelineArn"])["Tags"]
    assert tags[0]["Key"] == "TestKey"
    assert tags[0]["Value"] == "TestValue"


@mock_aws
def test_stop_pipeline():
    set_transition({"progression": "manual", "times": 2})
    client = boto3.client("osis", region_name="eu-west-1")
    client.create_pipeline(**BASIC_PIPELINE_KWARGS)

    with pytest.raises(ClientError) as exc:
        client.stop_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == "Only pipelines with one of the following statuses are eligible for stopping: ['UPDATE_FAILED', 'ACTIVE']. The current status is CREATING."
    )

    for _ in range(2):
        client.list_pipelines()
    client.stop_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    pipeline = client.list_pipelines()["Pipelines"][0]
    assert pipeline["Status"] == "STOPPING"

    for _ in range(2):
        client.get_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    pipeline = client.list_pipelines()["Pipelines"][0]
    assert pipeline["Status"] == "STOPPED"


@mock_aws
def test_start_pipeline():
    set_transition({"progression": "manual", "times": 2})
    client = boto3.client("osis", region_name="eu-west-1")
    client.create_pipeline(**BASIC_PIPELINE_KWARGS)

    with pytest.raises(ClientError) as exc:
        client.start_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    err = exc.value.response["Error"]
    assert err["Code"] == "ConflictException"
    assert (
        err["Message"]
        == "Only pipelines with one of the following statuses are eligible for starting: ['START_FAILED', 'STOPPED']. The current status is CREATING."
    )

    for _ in range(2):
        client.list_pipelines()

    client.stop_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])

    for _ in range(2):
        client.list_pipelines()

    client.start_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])
    pipeline = client.list_pipelines()["Pipelines"][0]
    assert pipeline["Status"] == "STARTING"
    client.list_pipelines()
    pipeline = client.list_pipelines()["Pipelines"][0]
    assert pipeline["Status"] == "ACTIVE"


@mock_aws
def test_tag_resource():
    client = boto3.client("osis", region_name="eu-west-1")
    resp = client.create_pipeline(**BASIC_PIPELINE_KWARGS)["Pipeline"]
    client.tag_resource(
        Arn=resp["PipelineArn"], Tags=[{"Key": "TestKey", "Value": "TestValue"}]
    )
    resp = client.get_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])[
        "Pipeline"
    ]
    assert resp["Tags"] == [{"Key": "TestKey", "Value": "TestValue"}]


@mock_aws
def test_untag_resource():
    client = boto3.client("osis", region_name="eu-west-1")
    resp = client.create_pipeline(
        **BASIC_PIPELINE_KWARGS, Tags=[{"Key": "TestKey", "Value": "TestValue"}]
    )["Pipeline"]
    client.untag_resource(Arn=resp["PipelineArn"], TagKeys=["TestKey"])
    resp = client.get_pipeline(PipelineName=BASIC_PIPELINE_KWARGS["PipelineName"])[
        "Pipeline"
    ]
    assert resp["Tags"] == []


def set_transition(transition={"progression": "immediate"}):
    if settings.TEST_DECORATOR_MODE:
        state_manager.set_transition(model_name="osis::pipeline", transition=transition)
    else:
        post_body = dict(model_name="osis::pipeline", transition=transition)
        requests.post(
            "http://localhost:5000/moto-api/state-manager/set-transition",
            data=json.dumps(post_body),
        )
