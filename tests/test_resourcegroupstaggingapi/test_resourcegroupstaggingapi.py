import json

import boto3
from botocore.client import ClientError

from moto import mock_ec2
from moto import mock_elbv2
from moto import mock_kms
from moto import mock_resourcegroupstaggingapi
from moto import mock_s3
from moto import mock_lambda
from moto import mock_iam
from moto import mock_cloudformation
from moto import mock_ecs
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2


@mock_kms
@mock_cloudformation
@mock_resourcegroupstaggingapi
def test_get_resources_cloudformation():

    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"test": {"Type": "AWS::S3::Bucket"}},
    }
    template_json = json.dumps(template)

    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_one = cf_client.create_stack(
        StackName="stack-1",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "one"}],
    ).get("StackId")
    stack_two = cf_client.create_stack(
        StackName="stack-2",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "two"}],
    ).get("StackId")
    stack_three = cf_client.create_stack(
        StackName="stack-3",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "three"}],
    ).get("StackId")

    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["one"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert stack_one in resp["ResourceTagMappingList"][0]["ResourceARN"]

    resp = rgta_client.get_resources(
        TagFilters=[{"Key": "tag", "Values": ["one", "three"]}]
    )
    assert len(resp["ResourceTagMappingList"]) == 2
    assert stack_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert stack_three in resp["ResourceTagMappingList"][1]["ResourceARN"]

    kms_client = boto3.client("kms", region_name="us-east-1")
    kms_client.create_key(
        KeyUsage="ENCRYPT_DECRYPT", Tags=[{"TagKey": "tag", "TagValue": "two"}]
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["two"]}])
    assert len(resp["ResourceTagMappingList"]) == 2
    assert stack_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert "kms" in resp["ResourceTagMappingList"][1]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["cloudformation:stack"],
        TagFilters=[{"Key": "tag", "Values": ["two"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert stack_two in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_ecs
@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_resources_ecs():

    # ecs:cluster
    client = boto3.client("ecs", region_name="us-east-1")
    cluster_one = (
        client.create_cluster(
            clusterName="cluster-a", tags=[{"key": "tag", "value": "a tag"}]
        )
        .get("cluster")
        .get("clusterArn")
    )
    cluster_two = (
        client.create_cluster(
            clusterName="cluster-b", tags=[{"key": "tag", "value": "b tag"}]
        )
        .get("cluster")
        .get("clusterArn")
    )

    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["a tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert cluster_one in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # ecs:service
    service_one = (
        client.create_service(
            cluster=cluster_one,
            serviceName="service-a",
            tags=[{"key": "tag", "value": "a tag"}],
        )
        .get("service")
        .get("serviceArn")
    )

    service_two = (
        client.create_service(
            cluster=cluster_two,
            serviceName="service-b",
            tags=[{"key": "tag", "value": "b tag"}],
        )
        .get("service")
        .get("serviceArn")
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["a tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 2
    assert service_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_one in resp["ResourceTagMappingList"][1]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:cluster"],
        TagFilters=[{"Key": "tag", "Values": ["b tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert service_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two in resp["ResourceTagMappingList"][0]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:service"],
        TagFilters=[{"Key": "tag", "Values": ["b tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert service_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # ecs:task
    resp = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc").get("VpcId")
    subnet = (
        ec2_client.create_subnet(VpcId=vpc, CidrBlock="10.0.0.0/18")
        .get("Subnet")
        .get("SubnetId")
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc, GroupName="test-ecs", Description="moto ecs"
    ).get("GroupId")

    task_one = (
        client.run_task(
            cluster="cluster-a",
            taskDefinition="test_ecs_task",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [subnet],
                    "securityGroups": [sg],
                }
            },
            tags=[{"key": "tag", "value": "a tag"}],
        )
        .get("tasks")[0]
        .get("taskArn")
    )

    task_two = (
        client.run_task(
            cluster="cluster-b",
            taskDefinition="test_ecs_task",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [subnet],
                    "securityGroups": [sg],
                }
            },
            tags=[{"key": "tag", "value": "b tag"}],
        )
        .get("tasks")[0]
        .get("taskArn")
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["b tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 3
    assert service_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two in resp["ResourceTagMappingList"][1]["ResourceARN"]
    assert task_two in resp["ResourceTagMappingList"][2]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:task"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert task_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert task_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_resources_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    instances = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_id = instances["Instances"][0]["InstanceId"]
    image_id = client.create_image(Name="testami", InstanceId=instance_id)["ImageId"]

    client.create_tags(Resources=[image_id], Tags=[{"Key": "ami", "Value": "test"}])

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_resources()
    # Check we have 1 entry for Instance, 1 Entry for AMI
    assert len(resp["ResourceTagMappingList"]) == 2

    # 1 Entry for AMI
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:image"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "image/" in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # As were iterating the same data, this rules out that the test above was a fluke
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:instance"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "instance/" in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # Basic test of tag filters
    resp = rtapi.get_resources(
        TagFilters=[{"Key": "MY_TAG1", "Values": ["MY_VALUE1", "some_other_value"]}]
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "instance/" in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_resources_ec2_vpc():
    ec2 = boto3.resource("ec2", region_name="us-west-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_tags(Resources=[vpc.id], Tags=[{"Key": "test", "Value": "test"}])

    def assert_response(resp):
        results = resp.get("ResourceTagMappingList", [])
        assert len(results) == 1
        assert vpc.id in results[0]["ResourceARN"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2"])
    assert_response(resp)
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:vpc"])
    assert_response(resp)
    resp = rtapi.get_resources(TagFilters=[{"Key": "test", "Values": ["test"]}])
    assert_response(resp)


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_tag_keys_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_tag_keys()

    assert "MY_TAG1" in resp["TagKeys"]
    assert "MY_TAG2" in resp["TagKeys"]
    assert "MY_TAG3" in resp["TagKeys"]

    # TODO test pagenation


@mock_ec2
@mock_resourcegroupstaggingapi
def test_get_tag_values_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE4"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE5"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE6"}],
            },
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_tag_values(Key="MY_TAG1")

    assert "MY_VALUE1" in resp["TagValues"]
    assert "MY_VALUE4" in resp["TagValues"]


@mock_ec2
@mock_elbv2
@mock_kms
@mock_resourcegroupstaggingapi
def test_get_many_resources():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    kms = boto3.client("kms", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    elbv2.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[
            {"Key": "key_name", "Value": "a_value"},
            {"Key": "key_2", "Value": "val2"},
        ],
    )

    elbv2.create_load_balancer(
        Name="my-other-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
    )

    kms.create_key(
        KeyUsage="ENCRYPT_DECRYPT",
        Tags=[
            {"TagKey": "key_name", "TagValue": "a_value"},
            {"TagKey": "key_2", "TagValue": "val2"},
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:loadbalancer"]
    )

    assert len(resp["ResourceTagMappingList"]) == 2
    assert "loadbalancer/" in resp["ResourceTagMappingList"][0]["ResourceARN"]
    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:loadbalancer"],
        TagFilters=[{"Key": "key_name"}],
    )

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "key_name", "Value": "a_value"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]

    # TODO test pagination


@mock_ec2
@mock_elbv2
@mock_resourcegroupstaggingapi
def test_get_resources_target_group():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")
    elbv2 = boto3.client("elbv2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Create two tagged target groups
    for i in range(1, 3):
        i_str = str(i)

        target_group = elbv2.create_target_group(
            Name="test" + i_str,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            TargetType="instance",
        )["TargetGroups"][0]

        elbv2.add_tags(
            ResourceArns=[target_group["TargetGroupArn"]],
            Tags=[{"Key": "Test", "Value": i_str}],
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["elasticloadbalancing:targetgroup"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:targetgroup"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_s3
@mock_resourcegroupstaggingapi
def test_get_resources_s3():
    # Tests pagination
    s3_client = boto3.client("s3", region_name="eu-central-1")

    # Will end up having key1,key2,key3,key4
    response_keys = set()

    # Create 4 buckets
    for i in range(1, 5):
        i_str = str(i)
        s3_client.create_bucket(
            Bucket="test_bucket" + i_str,
            CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
        )
        s3_client.put_bucket_tagging(
            Bucket="test_bucket" + i_str,
            Tagging={"TagSet": [{"Key": "key" + i_str, "Value": "value" + i_str}]},
        )
        response_keys.add("key" + i_str)

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_resources(ResourcesPerPage=2)
    for resource in resp["ResourceTagMappingList"]:
        response_keys.remove(resource["Tags"][0]["Key"])

    assert len(response_keys) == 2

    resp = rtapi.get_resources(
        ResourcesPerPage=2, PaginationToken=resp["PaginationToken"]
    )
    for resource in resp["ResourceTagMappingList"]:
        response_keys.remove(resource["Tags"][0]["Key"])

    assert len(response_keys) == 0


@mock_ec2
@mock_resourcegroupstaggingapi
def test_multiple_tag_filters():
    client = boto3.client("ec2", region_name="eu-central-1")

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_UNIQUE_VALUE"},
                    {"Key": "MY_TAG2", "Value": "MY_SHARED_VALUE"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_1_id = resp["Instances"][0]["InstanceId"]

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID2,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_ALT_UNIQUE_VALUE"},
                    {"Key": "MY_TAG2", "Value": "MY_SHARED_VALUE"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_ALT_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_2_id = resp["Instances"][0]["InstanceId"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    results = rtapi.get_resources(
        TagFilters=[
            {"Key": "MY_TAG1", "Values": ["MY_UNIQUE_VALUE"]},
            {"Key": "MY_TAG2", "Values": ["MY_SHARED_VALUE"]},
        ]
    ).get("ResourceTagMappingList", [])
    assert len(results) == 1
    assert instance_1_id in results[0]["ResourceARN"]
    assert instance_2_id not in results[0]["ResourceARN"]


@mock_lambda
@mock_resourcegroupstaggingapi
@mock_iam
def test_get_resources_lambda():
    def get_role_name():
        with mock_iam():
            iam = boto3.client("iam", region_name="us-west-2")
            try:
                return iam.get_role(RoleName="my-role")["Role"]["Arn"]
            except ClientError:
                return iam.create_role(
                    RoleName="my-role",
                    AssumeRolePolicyDocument="some policy",
                    Path="/my-path/",
                )["Role"]["Arn"]

    client = boto3.client("lambda", region_name="us-west-2")

    zipfile = """
              def lambda_handler(event, context):
                  print("custom log event")
                  return event
              """

    # create one lambda without tags
    client.create_function(
        FunctionName="lambda-no-tag",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    # create second & third lambda with tags
    circle_arn = client.create_function(
        FunctionName="lambda-tag-value-1",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Tags={"Color": "green", "Shape": "circle"},
    )["FunctionArn"]

    rectangle_arn = client.create_function(
        FunctionName="lambda-tag-value-2",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Tags={"Color": "green", "Shape": "rectangle"},
    )["FunctionArn"]

    def assert_response(response, expected_arns):
        results = response.get("ResourceTagMappingList", [])
        resultArns = []
        for item in results:
            resultArns.append(item["ResourceARN"])
        for arn in resultArns:
            assert arn in expected_arns
        for arn in expected_arns:
            assert arn in resultArns

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
    resp = rtapi.get_resources(ResourceTypeFilters=["lambda"])
    assert_response(resp, [circle_arn, rectangle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Color", "Values": ["green"]}])
    assert_response(resp, [circle_arn, rectangle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Shape", "Values": ["circle"]}])
    assert_response(resp, [circle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Shape", "Values": ["rectangle"]}])
    assert_response(resp, [rectangle_arn])


@mock_resourcegroupstaggingapi
def test_tag_resources_for_unknown_service():
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
    missing_resources = rtapi.tag_resources(
        ResourceARNList=["arn:aws:service_x"], Tags={"key1": "k", "key2": "v"}
    )["FailedResourcesMap"]

    assert "arn:aws:service_x" in missing_resources
    assert (
        missing_resources["arn:aws:service_x"]["ErrorCode"]
        == "InternalServiceException"
    )
