# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import boto3
from botocore.exceptions import ClientError
import pytest
from moto import mock_sagemaker

import sure  # noqa

from moto.sagemaker.models import VpcConfig


class MySageMakerModel(object):
    def __init__(self, name, arn, container=None, vpc_config=None):
        self.name = name
        self.arn = arn
        self.container = container if container else {}
        self.vpc_config = (
            vpc_config if vpc_config else {"sg-groups": ["sg-123"], "subnets": ["123"]}
        )

    def save(self):
        client = boto3.client("sagemaker", region_name="us-east-1")
        vpc_config = VpcConfig(
            self.vpc_config.get("sg-groups"), self.vpc_config.get("subnets")
        )
        client.create_model(
            ModelName=self.name,
            ExecutionRoleArn=self.arn,
            VpcConfig=vpc_config.response_object,
        )


@mock_sagemaker
def test_describe_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    test_model = MySageMakerModel(
        name="blah",
        arn="arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar",
        vpc_config={"sg-groups": ["sg-123"], "subnets": ["123"]},
    )
    test_model.save()
    model = client.describe_model(ModelName="blah")
    assert model.get("ModelName").should.equal("blah")


@mock_sagemaker
def test_describe_model_not_found():
    client = boto3.client("sagemaker", region_name="us-east-1")
    with pytest.raises(ClientError) as err:
        client.describe_model(ModelName="unknown")
    assert err.value.response["Error"]["Message"].should.contain("Could not find model")


@mock_sagemaker
def test_create_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    vpc_config = VpcConfig(["sg-foobar"], ["subnet-xxx"])
    exec_role_arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    name = "blah"
    model = client.create_model(
        ModelName=name,
        ExecutionRoleArn=exec_role_arn,
        VpcConfig=vpc_config.response_object,
    )

    model["ModelArn"].should.match(r"^arn:aws:sagemaker:.*:.*:model/{}$".format(name))


@mock_sagemaker
def test_delete_model():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model = MySageMakerModel(name=name, arn=arn)
    test_model.save()

    assert len(client.list_models()["Models"]).should.equal(1)
    client.delete_model(ModelName=name)
    assert len(client.list_models()["Models"]).should.equal(0)


@mock_sagemaker
def test_delete_model_not_found():
    with pytest.raises(ClientError) as err:
        boto3.client("sagemaker", region_name="us-east-1").delete_model(
            ModelName="blah"
        )
    assert err.value.response["Error"]["Code"].should.equal("404")


@mock_sagemaker
def test_list_models():
    client = boto3.client("sagemaker", region_name="us-east-1")
    name = "blah"
    arn = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model = MySageMakerModel(name=name, arn=arn)
    test_model.save()
    models = client.list_models()
    assert len(models["Models"]).should.equal(1)
    assert models["Models"][0]["ModelName"].should.equal(name)
    assert models["Models"][0]["ModelArn"].should.match(
        r"^arn:aws:sagemaker:.*:.*:model/{}$".format(name)
    )


@mock_sagemaker
def test_list_models_multiple():
    client = boto3.client("sagemaker", region_name="us-east-1")

    name_model_1 = "blah"
    arn_model_1 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model_1 = MySageMakerModel(name=name_model_1, arn=arn_model_1)
    test_model_1.save()

    name_model_2 = "blah2"
    arn_model_2 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar2"
    test_model_2 = MySageMakerModel(name=name_model_2, arn=arn_model_2)
    test_model_2.save()
    models = client.list_models()
    assert len(models["Models"]).should.equal(2)


@mock_sagemaker
def test_list_models_none():
    client = boto3.client("sagemaker", region_name="us-east-1")
    models = client.list_models()
    assert len(models["Models"]).should.equal(0)
