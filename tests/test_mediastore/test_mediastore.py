from __future__ import unicode_literals

import boto3
import sure  # noqa
from moto import mock_mediastore

region = "eu-west-1"



def _create_lifecycle_policy_config(**kwargs):
    container_name = kwargs.get("container_name", "container-name")
    lifecycle_policy = kwargs.get("lifecycle_policy", "lifecycle-policy")
    policy_config = dict(ContainerName=container_name, LifecyclePolicy=lifecycle_policy,)
    return policy_config

@mock_mediastore
def test_put_lifecycle_policy_succeeds():
    client = boto3.client("mediastore", region_name=region)
    policy_config = _create_lifecycle_policy_config()
    print(policy_config)
    client.put_lifecycle_policy(**policy_config)
    # response["ContainerName"].should.equal("container-name")

    