# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import boto3
from botocore.exceptions import ClientError, ParamValidationError
import sure  # noqa

from moto import mock_sagemaker
from moto.sts.models import ACCOUNT_ID
from nose.tools import assert_true, assert_equal, assert_raises

TEST_REGION_NAME = "us-east-1"
FAKE_ROLE_ARN = "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
GENERIC_TAGS_PARAM = [
    {"Key": "newkey1", "Value": "newval1"},
    {"Key": "newkey2", "Value": "newval2"},
]


@mock_sagemaker
def test_create_endpoint_config():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    model_name = "MyModel"
    production_variants = [
        {
            "VariantName": "MyProductionVariant",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium",
        },
    ]

    endpoint_config_name = "MyEndpointConfig"
    with assert_raises(ClientError) as e:
        sagemaker.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=production_variants,
        )
    assert_true(
        e.exception.response["Error"]["Message"].startswith("Could not find model")
    )

    _create_model(sagemaker, model_name)
    resp = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name, ProductionVariants=production_variants
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(endpoint_config_name)
    )

    resp = sagemaker.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(endpoint_config_name)
    )
    resp["EndpointConfigName"].should.equal(endpoint_config_name)
    resp["ProductionVariants"].should.equal(production_variants)


@mock_sagemaker
def test_delete_endpoint_config():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    model_name = "MyModel"
    _create_model(sagemaker, model_name)

    endpoint_config_name = "MyEndpointConfig"
    production_variants = [
        {
            "VariantName": "MyProductionVariant",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium",
        },
    ]

    resp = sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name, ProductionVariants=production_variants
    )
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(endpoint_config_name)
    )

    resp = sagemaker.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
    resp["EndpointConfigArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint-config/{}$".format(endpoint_config_name)
    )

    resp = sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
    with assert_raises(ClientError) as e:
        sagemaker.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
    assert_true(
        e.exception.response["Error"]["Message"].startswith(
            "Could not find endpoint configuration"
        )
    )

    with assert_raises(ClientError) as e:
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
    assert_true(
        e.exception.response["Error"]["Message"].startswith(
            "Could not find endpoint configuration"
        )
    )
    pass


@mock_sagemaker
def test_create_endpoint_invalid_instance_type():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    model_name = "MyModel"
    _create_model(sagemaker, model_name)

    instance_type = "InvalidInstanceType"
    production_variants = [
        {
            "VariantName": "MyProductionVariant",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": instance_type,
        },
    ]

    endpoint_config_name = "MyEndpointConfig"
    with assert_raises(ClientError) as e:
        sagemaker.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=production_variants,
        )
    assert_equal(e.exception.response["Error"]["Code"], "ValidationException")
    expected_message = "Value '{}' at 'instanceType' failed to satisfy constraint: Member must satisfy enum value set: [".format(
        instance_type
    )
    assert_true(expected_message in e.exception.response["Error"]["Message"])


@mock_sagemaker
def test_create_endpoint():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    endpoint_name = "MyEndpoint"
    with assert_raises(ClientError) as e:
        sagemaker.create_endpoint(
            EndpointName=endpoint_name, EndpointConfigName="NonexistentEndpointConfig"
        )
    assert_true(
        e.exception.response["Error"]["Message"].startswith(
            "Could not find endpoint configuration"
        )
    )

    model_name = "MyModel"
    _create_model(sagemaker, model_name)

    endpoint_config_name = "MyEndpointConfig"
    _create_endpoint_config(sagemaker, endpoint_config_name, model_name)

    resp = sagemaker.create_endpoint(
        EndpointName=endpoint_name,
        EndpointConfigName=endpoint_config_name,
        Tags=GENERIC_TAGS_PARAM,
    )
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(endpoint_name)
    )

    resp = sagemaker.describe_endpoint(EndpointName=endpoint_name)
    resp["EndpointArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:endpoint/{}$".format(endpoint_name)
    )
    resp["EndpointName"].should.equal(endpoint_name)
    resp["EndpointConfigName"].should.equal(endpoint_config_name)
    resp["EndpointStatus"].should.equal("InService")
    assert_true(isinstance(resp["CreationTime"], datetime.datetime))
    assert_true(isinstance(resp["LastModifiedTime"], datetime.datetime))
    resp["ProductionVariants"][0]["VariantName"].should.equal("MyProductionVariant")

    resp = sagemaker.list_tags(ResourceArn=resp["EndpointArn"])
    assert_equal(resp["Tags"], GENERIC_TAGS_PARAM)


@mock_sagemaker
def test_delete_endpoint():
    sagemaker = boto3.client("sagemaker", region_name=TEST_REGION_NAME)

    model_name = "MyModel"
    _create_model(sagemaker, model_name)

    endpoint_config_name = "MyEndpointConfig"
    _create_endpoint_config(sagemaker, endpoint_config_name, model_name)

    endpoint_name = "MyEndpoint"
    _create_endpoint(sagemaker, endpoint_name, endpoint_config_name)

    sagemaker.delete_endpoint(EndpointName=endpoint_name)
    with assert_raises(ClientError) as e:
        sagemaker.describe_endpoint(EndpointName=endpoint_name)
    assert_true(
        e.exception.response["Error"]["Message"].startswith("Could not find endpoint")
    )

    with assert_raises(ClientError) as e:
        sagemaker.delete_endpoint(EndpointName=endpoint_name)
    assert_true(
        e.exception.response["Error"]["Message"].startswith("Could not find endpoint")
    )


def _create_model(boto_client, model_name):
    resp = boto_client.create_model(
        ModelName=model_name,
        PrimaryContainer={
            "Image": "382416733822.dkr.ecr.us-east-1.amazonaws.com/factorization-machines:1",
            "ModelDataUrl": "s3://MyBucket/model.tar.gz",
        },
        ExecutionRoleArn=FAKE_ROLE_ARN,
    )
    assert_equal(resp["ResponseMetadata"]["HTTPStatusCode"], 200)


def _create_endpoint_config(boto_client, endpoint_config_name, model_name):
    production_variants = [
        {
            "VariantName": "MyProductionVariant",
            "ModelName": model_name,
            "InitialInstanceCount": 1,
            "InstanceType": "ml.t2.medium",
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
