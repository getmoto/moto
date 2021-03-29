from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_mediastore

region = "eu-west-1"


@mock_mediastore
# def test_create_channel_succeeds():
#     client = boto3.client("mediastore", region_name=region)
#     response = client.create_container(
#         ContainerName="Awesome container!", Tags=[{"Key": "customer"}]
#     )
#     print(response)
#     container = response["Container"]
#     response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
#     container["ARN"].should.equal(
#         "arn:aws:mediastore:container:{}".format(container["Name"])
#     )
#     container["Name"].should.equal("Awesome container!")
#     container["Status"].should.equal("ACTIVE")
#     container["Tags"][0]["Key"].should.equal("customer")


@mock_mediastore
def test_put_lifecycle_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    container_response = client.create_container(
        ContainerName="container-name", Tags=[{"Key": "customer"}]
    )
    container = container_response["Container"]
    print(container)
    response = client.put_lifecycle_policy(
        ContainerName=container["Name"], LifecyclePolicy="lifecycle-policy"
    )
    print(response)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["LifeCyclePolicy"].should.equal("lifecycle-policy")