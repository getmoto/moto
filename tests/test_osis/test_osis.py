"""Unit tests for osis-supported APIs."""

import boto3
import json

from moto import mock_aws
from tests.test_opensearchserverless.test_opensearchserverless import ENCRYPTION_POLICY

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html

def create_os_domain() -> str:
    client = boto3.client("opensearch", region_name="eu-west-1")
    return client.create_domain(DomainName="testdn")["DomainStatus"]


def create_oss_collection() -> str:
    client = boto3.client("opensearchserverless", region_name="eu-west-1")
    client.create_security_policy(name="test-policy", policy=ENCRYPTION_POLICY, type="encryption")
    return client.create_collection(name="col-foobar")["createCollectionDetail"]["id"]


@mock_aws
def test_create_pipeline():
    client = boto3.client("osis", region_name="eu-west-1")
    collection_id = create_oss_collection()
    kwargs = {
        "PipelineName": "test",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": 'version: "2"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: ["https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]\n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:\n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"\n        serverless: false\n  sink:\n    - opensearch:\n        hosts: ["https://{}.eu-west-1.aoss.amazonaws.com"]\n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"\n          region: "eu-west-1"\n          serverless: true\n'.format(collection_id),
    }
    resp = client.create_pipeline(**kwargs)["Pipeline"]
    assert resp["PipelineName"] == "test"
    assert resp["MinUnits"] == 2
    assert resp["MaxUnits"] == 4
    assert resp["Status"] == "ACTIVE"
    assert resp["StatusReason"]["Description"] == "The pipeline is ready to ingest data."
    assert resp["PipelineConfigurationBody"] == kwargs["PipelineConfigurationBody"]
    assert ".eu-west-1.osis.amazonaws.com" in resp["IngestEndpointUrls"][0] and "test" in resp["IngestEndpointUrls"][0]
    assert resp["ServiceVpcEndpoints"][0]["ServiceName"] == "OPENSEARCH_SERVERLESS"
    assert resp["Destinations"][0]["ServiceName"] == "OpenSearch_Serverless"
    assert resp["Destinations"][0]["Endpoint"] == f"https://{collection_id}.eu-west-1.aoss.amazonaws.com"
    assert "VpcEndpointService" not in resp


    domain_endpoint = create_os_domain()
    import pdb; pdb.set_trace()
    kwargs = {
        "PipelineName": "test-2",
        "MinUnits": 2,
        "MaxUnits": 4,
        "PipelineConfigurationBody": 'version: "2"\nopensearch-migration-pipeline:\n  source:\n    opensearch:\n      acknowledgments: true\n      hosts: ["https://vpc-c7ntest-ieeljhbsnht35i5rtzjl756pk4.eu-west-1.es.amazonaws.com"]\n      indices:\n        exclude:\n          - index_name_regex: \'\\..*\'\n      aws:\n        region: "eu-west-1"\n        sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"\n        serverless: false\n  sink:\n    - opensearch:\n        hosts: ["{}}"]\n        aws:\n          sts_role_arn: "arn:aws:iam::123456789012:role/MyRole"\n          region: "eu-west-1"\n          serverless: false\n'.format(domain_endpoint),
    }
    resp = client.create_pipeline(**kwargs)["Pipeline"]




# @mock_aws
# def test_delete_pipeline():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.delete_pipeline()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_get_pipeline():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.get_pipeline()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_pipelines():
#     client = boto3.client("osis", region_name="ap-southeast-1")
#     resp = client.list_pipelines()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_list_tags_for_resource():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.list_tags_for_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_update_pipeline():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.update_pipeline()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_tag_resource():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.tag_resource()

#     raise Exception("NotYetImplemented")


# @mock_aws
# def test_untag_resource():
#     client = boto3.client("osis", region_name="eu-west-1")
#     resp = client.untag_resource()

#     raise Exception("NotYetImplemented")
