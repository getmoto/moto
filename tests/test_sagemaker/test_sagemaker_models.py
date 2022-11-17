import boto3
from botocore.exceptions import ClientError
import pytest
from moto import mock_sagemaker

import sure  # noqa # pylint: disable=unused-import

from moto.sagemaker.models import VpcConfig

TEST_REGION_NAME = "us-east-1"
TEST_ARN = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
TEST_MODEL_NAME = "MyModelName"


@pytest.fixture(name="sagemaker_client")
def fixture_sagemaker_client():
    with mock_sagemaker():
        yield boto3.client("sagemaker", region_name=TEST_REGION_NAME)


class MySageMakerModel(object):
    def __init__(self, name=None, arn=None, container=None, vpc_config=None):
        self.name = name or TEST_MODEL_NAME
        self.arn = arn or TEST_ARN
        self.container = container or {}
        self.vpc_config = vpc_config or {"sg-groups": ["sg-123"], "subnets": ["123"]}

    def save(self, sagemaker_client):
        vpc_config = VpcConfig(
            self.vpc_config.get("sg-groups"), self.vpc_config.get("subnets")
        )
        resp = sagemaker_client.create_model(
            ModelName=self.name,
            ExecutionRoleArn=self.arn,
            VpcConfig=vpc_config.response_object,
        )
        return resp


def test_describe_model(sagemaker_client):
    test_model = MySageMakerModel()
    test_model.save(sagemaker_client)
    model = sagemaker_client.describe_model(ModelName=TEST_MODEL_NAME)
    assert model.get("ModelName").should.equal(TEST_MODEL_NAME)


def test_describe_model_not_found(sagemaker_client):
    with pytest.raises(ClientError) as err:
        sagemaker_client.describe_model(ModelName="unknown")
    assert err.value.response["Error"]["Message"].should.contain("Could not find model")


def test_create_model(sagemaker_client):
    vpc_config = VpcConfig(["sg-foobar"], ["subnet-xxx"])
    model = sagemaker_client.create_model(
        ModelName=TEST_MODEL_NAME,
        ExecutionRoleArn=TEST_ARN,
        VpcConfig=vpc_config.response_object,
    )
    model["ModelArn"].should.match(
        rf"^arn:aws:sagemaker:.*:.*:model/{TEST_MODEL_NAME}$"
    )


def test_delete_model(sagemaker_client):
    test_model = MySageMakerModel()
    test_model.save(sagemaker_client)

    assert len(sagemaker_client.list_models()["Models"]).should.equal(1)
    sagemaker_client.delete_model(ModelName=TEST_MODEL_NAME)
    assert len(sagemaker_client.list_models()["Models"]).should.equal(0)


def test_delete_model_not_found(sagemaker_client):
    with pytest.raises(ClientError) as err:
        sagemaker_client.delete_model(ModelName="blah")
    assert err.value.response["Error"]["Code"].should.equal("404")


def test_list_models(sagemaker_client):
    test_model = MySageMakerModel()
    test_model.save(sagemaker_client)
    models = sagemaker_client.list_models()
    assert len(models["Models"]).should.equal(1)
    assert models["Models"][0]["ModelName"].should.equal(TEST_MODEL_NAME)
    assert models["Models"][0]["ModelArn"].should.match(
        rf"^arn:aws:sagemaker:.*:.*:model/{TEST_MODEL_NAME}$"
    )


def test_list_models_multiple(sagemaker_client):
    name_model_1 = "blah"
    arn_model_1 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar"
    test_model_1 = MySageMakerModel(name=name_model_1, arn=arn_model_1)
    test_model_1.save(sagemaker_client)

    name_model_2 = "blah2"
    arn_model_2 = "arn:aws:sagemaker:eu-west-1:000000000000:x-x/foobar2"
    test_model_2 = MySageMakerModel(name=name_model_2, arn=arn_model_2)
    test_model_2.save(sagemaker_client)
    models = sagemaker_client.list_models()
    assert len(models["Models"]).should.equal(2)


def test_list_models_none(sagemaker_client):
    models = sagemaker_client.list_models()
    assert len(models["Models"]).should.equal(0)


def test_add_tags_to_model(sagemaker_client):
    model = MySageMakerModel().save(sagemaker_client)
    resource_arn = model["ModelArn"]

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == tags


def test_delete_tags_from_model(sagemaker_client):
    model = MySageMakerModel().save(sagemaker_client)
    resource_arn = model["ModelArn"]

    tags = [
        {"Key": "myKey", "Value": "myValue"},
    ]
    response = sagemaker_client.add_tags(ResourceArn=resource_arn, Tags=tags)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    tag_keys = [tag["Key"] for tag in tags]
    response = sagemaker_client.delete_tags(ResourceArn=resource_arn, TagKeys=tag_keys)
    assert response["ResponseMetadata"]["HTTPStatusCode"] == 200

    response = sagemaker_client.list_tags(ResourceArn=resource_arn)
    assert response["Tags"] == []
