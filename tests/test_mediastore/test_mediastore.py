from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_mediastore

region = "eu-west-1"

@mock_mediastore
def test_create_channel_succeeds():
    client = boto3.client("mediastore", region_name=region)
    response = client.create_container(ContainerName="Awesome container!", Tags=[{"Key": "customer"}])
    print(response)
    response["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)
    response["Arn"].should.equal(
         "arn:aws:mediastore:container:{}".format(response["Name"])
    )
    response["Name"].should.equal("Awesome container!")
    response["Status"].should.equal("ACTIVE")
    response["Tags"][0]["Key"].should.equal("customer")

@mock_mediastore
def test_put_lifecycle_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    container = client.create_container(ContainerName="container-name", Tags=[{"Key": "customer"}])
    print(container)
    response = client.put_lifecycle_policy(container["ContainerName"], "lifecycle-policy")
    print(response)
#   response["ContainerName"].should.equal("container-name")

    