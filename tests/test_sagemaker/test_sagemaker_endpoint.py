import datetime
import uuid

import boto3
from botocore.exceptions import ClientError
import sure  # noqa # pylint: disable=unused-import

from moto import mock_sagemaker
from moto.core import ACCOUNT_ID
import pytest

TEST_REGION_NAME = "us-east-1"
TEST_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
GENERIC_TAGS_PARAM = [
    {"Key": "newkey1", "Value": "newval1"},
    {"Key": "newkey2", "Value": "newval2"},
]
TEST_MODEL_NAME = "MyModel"
TEST_ENDPOINT_NAME = "MyEndpoint"
TEST_ENDPOINT_CONFIG_NAME = "MyEndpointConfig"
TEST_VARIANT_NAME = "MyProductionVariant"
TEST_INSTANCE_TYPE = "ml.t2.medium"
TEST_PRODUCTION_VARIANTS = [
    {
        "VariantName": TEST_VARIANT_NAME,
        "ModelName": TEST_MODEL_NAME,
        "InitialInstanceCount": 1,
        "InstanceType": TEST_INSTANCE_TYPE,
    },
]


@pytest.fixture
def sagemaker_client():
    return boto3.client("sagemaker", region_name=TEST_REGION_NAME)


@mock_sagemaker
def test_create_endpoint_config(sagemaker_client):
    with pytest.raises(ClientError) as e:
        sagemaker_client.create_endpoint_config(
            EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME,
            ProductionVariants=TEST_PRODUCTION_VARIANTS,
        )
    assert e.value.response["Error"]["Message"].startswith("Could not find model")

    _create_model(sagemaker_client, TEST_MODEL_NAME)
    resp = sagemaker_client.create_endpoint_config(
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME,
        ProductionVariants=TEST_PRODUCTION_VARIANTS,
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(
            TEST_ENDPOINT_CONFIG_NAME
        )
    )

    resp = sagemaker_client.describe_endpoint_config(
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(
            TEST_ENDPOINT_CONFIG_NAME
        )
    )
    resp["EndpointConfigName"].should.equal(TEST_ENDPOINT_CONFIG_NAME)
    resp["ProductionVariants"].should.equal(TEST_PRODUCTION_VARIANTS)


@mock_sagemaker
def test_delete_endpoint_config(sagemaker_client):
    _create_model(sagemaker_client, TEST_MODEL_NAME)
    resp = sagemaker_client.create_endpoint_config(
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME,
        ProductionVariants=TEST_PRODUCTION_VARIANTS,
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(
            TEST_ENDPOINT_CONFIG_NAME
        )
    )

    resp = sagemaker_client.describe_endpoint_config(
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(
            TEST_ENDPOINT_CONFIG_NAME
        )
    )

    sagemaker_client.delete_endpoint_config(
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME
    )
    with pytest.raises(ClientError) as e:
        sagemaker_client.describe_endpoint_config(
            EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME
        )
    assert e.value.response["Error"]["Message"].startswith(
        "Could not find endpoint configuration"
    )

    with pytest.raises(ClientError) as e:
        sagemaker_client.delete_endpoint_config(
            EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME
        )
    assert e.value.response["Error"]["Message"].startswith(
        "Could not find endpoint configuration"
    )


@mock_sagemaker
def test_create_endpoint_invalid_instance_type(sagemaker_client):
    _create_model(sagemaker_client, TEST_MODEL_NAME)

    instance_type = "InvalidInstanceType"
    production_variants = TEST_PRODUCTION_VARIANTS
    production_variants[0]["InstanceType"] = instance_type

    with pytest.raises(ClientError) as e:
        sagemaker_client.create_endpoint_config(
            EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME,
            ProductionVariants=production_variants,
        )
    assert e.value.response["Error"]["Code"] == "ValidationException"
    expected_message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: [".format(
        instance_type
    )
    assert expected_message in e.value.response["Error"]["Message"]


@mock_sagemaker
def test_create_endpoint(sagemaker_client):
    with pytest.raises(ClientError) as e:
        sagemaker_client.create_endpoint(
            EndpointName=TEST_ENDPOINT_NAME,
            EndpointConfigName="NonexistentEndpointConfig",
        )
    assert e.value.response["Error"]["Message"].startswith(
        "Could not find endpoint configuration"
    )

    _create_model(sagemaker_client, TEST_MODEL_NAME)

    _create_endpoint_config(
        sagemaker_client, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    resp = sagemaker_client.create_endpoint(
        EndpointName=TEST_ENDPOINT_NAME,
        EndpointConfigName=TEST_ENDPOINT_CONFIG_NAME,
        Tags=GENERIC_TAGS_PARAM,
    )
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )
    resp["EndpointName"].should.equal(TEST_ENDPOINT_NAME)
    resp["EndpointConfigName"].should.equal(TEST_ENDPOINT_CONFIG_NAME)
    resp["EndpointStatus"].should.equal("InService")
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)
    resp["ProductionVariants"][0]["VariantName"].should.equal(TEST_VARIANT_NAME)

    resp = sagemaker_client.list_tags(ResourceArn=resp["EndpointArn"])
    assert resp["Tags"] == GENERIC_TAGS_PARAM


@mock_sagemaker
def test_delete_endpoint(sagemaker_client):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    sagemaker_client.delete_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    with pytest.raises(ClientError) as e:
        sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    assert e.value.response["Error"]["Message"].startswith("Could not find endpoint")

    with pytest.raises(ClientError) as e:
        sagemaker_client.delete_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    assert e.value.response["Error"]["Message"].startswith("Could not find endpoint")


@mock_sagemaker
def test_add_tags_endpoint(sagemaker_client):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    resource_arn = f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:endpoint/{TEST_ENDPOINT_NAME}"
    response = sagemaker_client.add_tags(
        ResourceArn=resource_arn, Tags=GENERIC_TAGS_PARAM
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == GENERIC_TAGS_PARAM


@mock_sagemaker
def test_delete_tags_endpoint(sagemaker_client):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    resource_arn = f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:endpoint/{TEST_ENDPOINT_NAME}"
    response = sagemaker_client.add_tags(
        ResourceArn=resource_arn, Tags=GENERIC_TAGS_PARAM
    )
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    tag_keys = [tag["Key"] for tag in GENERIC_TAGS_PARAM]
    response = sagemaker_client.delete_tags(ResourceArn=resource_arn, TagKeys=tag_keys)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == []


@mock_sagemaker
def test_list_tags_endpoint(sagemaker_client):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    tags = []
    for _ in range(80):
        tags.append({"Key": str(uuid.uuid4()), "Value": "myValue"})

    resource_arn = f"arn:aws:sagemaker:{TEST_REGION_NAME}:{ACCOUNT_ID}:endpoint/{TEST_ENDPOINT_NAME}"
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert len(response["Tags"]) == 50
    assert response["Tags"] == tags[:50]

    response = sagemaker_client.list_tags(
        ResourceArn=resource_arn, NextToken=response["NextToken"]
    )
    assert len(response["Tags"]) == 30
    assert response["Tags"] == tags[50:]


@mock_sagemaker
def test_update_endpoint_weights_and_capacities_one_variant(sagemaker_client):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    new_desired_weight = 1.5
    new_desired_instance_count = 123

    response = sagemaker_client.update_endpoint_weights_and_capacities(
        EndpointName=TEST_ENDPOINT_NAME,
        DesiredWeightsAndCapacities=[
            {
                "VariantName": TEST_VARIANT_NAME,
                "DesiredWeight": new_desired_weight,
                "DesiredInstanceCount": new_desired_instance_count,
            },
        ],
    )
    response["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )
    resp["EndpointName"].should.equal(TEST_ENDPOINT_NAME)
    resp["EndpointConfigName"].should.equal(TEST_ENDPOINT_CONFIG_NAME)
    resp["EndpointStatus"].should.equal("InService")
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)

    resp["ProductionVariants"][0]["VariantName"].should.equal(TEST_VARIANT_NAME)
    resp["ProductionVariants"][0]["DesiredInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][0]["CurrentInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][0]["DesiredWeight"].should.equal(new_desired_weight)
    resp["ProductionVariants"][0]["CurrentWeight"].should.equal(new_desired_weight)


@mock_sagemaker
def test_update_endpoint_weights_and_capacities_two_variants(sagemaker_client):
    production_variants = [
        {
            "VariantName": "MyProductionVariant1",
            "ModelName": TEST_MODEL_NAME,
            "InitialInstanceCount": 1,
            "InstanceType": TEST_INSTANCE_TYPE,
        },
        {
            "VariantName": "MyProductionVariant2",
            "ModelName": TEST_MODEL_NAME,
            "InitialInstanceCount": 1,
            "InstanceType": TEST_INSTANCE_TYPE,
        },
    ]

    _set_up_sagemaker_resources(
        sagemaker_client,
        TEST_ENDPOINT_NAME,
        TEST_ENDPOINT_CONFIG_NAME,
        TEST_MODEL_NAME,
        production_variants,
    )

    desired_weights_and_capacities = [
        {
            "VariantName": "MyProductionVariant1",
            "DesiredWeight": 1.5,
            "DesiredInstanceCount": 123,
        },
        {
            "VariantName": "MyProductionVariant2",
            "DesiredWeight": 1.5,
            "DesiredInstanceCount": 123,
        },
    ]

    new_desired_weight = 1.5
    new_desired_instance_count = 123

    response = sagemaker_client.update_endpoint_weights_and_capacities(
        EndpointName=TEST_ENDPOINT_NAME,
        DesiredWeightsAndCapacities=desired_weights_and_capacities,
    )
    response["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(TEST_ENDPOINT_NAME)
    )
    resp["EndpointName"].should.equal(TEST_ENDPOINT_NAME)
    resp["EndpointConfigName"].should.equal(TEST_ENDPOINT_CONFIG_NAME)
    resp["EndpointStatus"].should.equal("InService")
    assert isinstance(resp["CreationTime"], datetime.datetime)
    assert isinstance(resp["LastModifiedTime"], datetime.datetime)

    resp["ProductionVariants"][0]["VariantName"].should.equal("MyProductionVariant1")
    resp["ProductionVariants"][0]["DesiredInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][0]["CurrentInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][0]["DesiredWeight"].should.equal(new_desired_weight)
    resp["ProductionVariants"][0]["CurrentWeight"].should.equal(new_desired_weight)

    resp["ProductionVariants"][1]["VariantName"].should.equal("MyProductionVariant2")
    resp["ProductionVariants"][1]["DesiredInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][1]["CurrentInstanceCount"].should.equal(
        new_desired_instance_count
    )
    resp["ProductionVariants"][1]["DesiredWeight"].should.equal(new_desired_weight)
    resp["ProductionVariants"][1]["CurrentWeight"].should.equal(new_desired_weight)


@mock_sagemaker
def test_update_endpoint_weights_and_capacities_should_throw_clienterror_no_variant(
    sagemaker_client,
):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    old_resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del old_resp["ResponseMetadata"]

    variant_name = "SillyNotCorrectName"
    new_desired_weight = 1.5
    new_desired_instance_count = 123

    with pytest.raises(ClientError) as exc:
        sagemaker_client.update_endpoint_weights_and_capacities(
            EndpointName=TEST_ENDPOINT_NAME,
            DesiredWeightsAndCapacities=[
                {
                    "VariantName": variant_name,
                    "DesiredWeight": new_desired_weight,
                    "DesiredInstanceCount": new_desired_instance_count,
                },
            ],
        )

    err = exc.value.response["Error"]
    err["Message"].should.equal(
        f'The variant name(s) "{variant_name}" is/are not present within endpoint configuration "{TEST_ENDPOINT_CONFIG_NAME}".'
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del resp["ResponseMetadata"]
    resp.should.equal(old_resp)


@mock_sagemaker
def test_update_endpoint_weights_and_capacities_should_throw_clienterror_no_endpoint(
    sagemaker_client,
):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    old_resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del old_resp["ResponseMetadata"]

    endpoint_name = "SillyEndpointName"
    variant_name = "SillyNotCorrectName"
    new_desired_weight = 1.5
    new_desired_instance_count = 123

    with pytest.raises(ClientError) as exc:
        sagemaker_client.update_endpoint_weights_and_capacities(
            EndpointName=endpoint_name,
            DesiredWeightsAndCapacities=[
                {
                    "VariantName": variant_name,
                    "DesiredWeight": new_desired_weight,
                    "DesiredInstanceCount": new_desired_instance_count,
                },
            ],
        )

    err = exc.value.response["Error"]
    err["Message"].should.equal(
        f'Could not find endpoint "arn:aws:sagemaker:us-east-1:{ACCOUNT_ID}:endpoint/{endpoint_name}".'
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del resp["ResponseMetadata"]
    resp.should.equal(old_resp)


@mock_sagemaker
def test_update_endpoint_weights_and_capacities_should_throw_clienterror_nonunique_variant(
    sagemaker_client,
):
    _set_up_sagemaker_resources(
        sagemaker_client, TEST_ENDPOINT_NAME, TEST_ENDPOINT_CONFIG_NAME, TEST_MODEL_NAME
    )

    old_resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del old_resp["ResponseMetadata"]

    desired_weights_and_capacities = [
        {
            "VariantName": TEST_VARIANT_NAME,
            "DesiredWeight": 1.5,
            "DesiredInstanceCount": 123,
        },
        {
            "VariantName": TEST_VARIANT_NAME,
            "DesiredWeight": 1.5,
            "DesiredInstanceCount": 123,
        },
    ]

    with pytest.raises(ClientError) as exc:
        sagemaker_client.update_endpoint_weights_and_capacities(
            EndpointName=TEST_ENDPOINT_NAME,
            DesiredWeightsAndCapacities=desired_weights_and_capacities,
        )

    err = exc.value.response["Error"]
    err["Message"].should.equal(
        f'The variant name "{TEST_VARIANT_NAME}" was non-unique within the request.'
    )

    resp = sagemaker_client.describe_endpoint(EndpointName=TEST_ENDPOINT_NAME)
    del resp["ResponseMetadata"]
    resp.should.equal(old_resp)


def _set_up_sagemaker_resources(
    boto_client,
    endpoint_name,
    endpoint_config_name,
    model_name,
    production_variants=None,
):
    _create_model(boto_client, model_name)
    _create_endpoint_config(
        boto_client, endpoint_config_name, model_name, production_variants
    )
    _create_endpoint(boto_client, endpoint_name, endpoint_config_name)


def _create_model(boto_client, model_name):
    resp = boto_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            "Image": "382416733822.dkr.ecr.us-east-1.amazonaws.com/factorization-machines:1",
            "ModelDataUrl": "s3://MyBucket/model.tar.gz",
        },
        ExecutionRoleArn=TEST_ROLE_ARN,
    )
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200


def _create_endpoint_config(
    boto_client, endpoint_config_name, model_name, production_variants=None
):
    if not production_variants:
        production_variants = [
            {
                "VariantName": TEST_VARIANT_NAME,
                "ModelName": model_name,
                "InitialInstanceCount": 1,
                "InstanceType": TEST_INSTANCE_TYPE,
            },
        ]
    resp = boto_client.create_endpoint_config(
        EndpointConfigName=endpoint_config_name, ProductionVariants=production_variants
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(endpoint_config_name)
    )


def _create_endpoint(boto_client, endpoint_name, endpoint_config_name):
    resp = boto_client.create_endpoint(
        EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name
    )
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(endpoint_name)
    )
