"""Unit tests for bedrockagent-supported APIs."""

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws

DEFAULT_REGION = "us-east-1"

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)

    resp = client.create_agent(
        agentName="agent_name",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    # resp = client.create_agent(
    #     agentName="agent_name",
    #     clientToken="client_tokenclient_tokenclient_token",
    #     instruction="instructioninstructioninstructioninstruction",
    #     foundationModel="foundation_model",
    #     description="description",
    #     idleSessionTTLInSeconds=60,
    #     agentResourceRoleArn="agent_resource_role_arn",
    #     customerEncryptionKeyArn="customer_encryption_key_arn",
    #     tags={
    #             "Key": "test-tag-key",
    #         },
    #     promptOverrideConfiguration={
    #     'promptConfigurations': [
    #         {
    #             'promptType': 'PRE_PROCESSING',
    #             'promptCreationMode': 'DEFAULT',
    #             'promptState': 'ENABLED',
    #             'basePromptTemplate': 'string',
    #             'inferenceConfiguration': {
    #                 'temperature': 1.0,
    #                 'topP': 1.0,
    #                 'topK': 123,
    #                 'maximumLength': 123,
    #                 'stopSequences': [
    #                     'string',
    #                 ]
    #             },
    #             'parserMode': 'DEFAULT'
    #         },
    #     ],
    #     'overrideLambda': 'overrideLambdaoverrideLambdaoverrideLambdaoverrideLambda'
    # }
    # )
    assert resp["agent"]["agentName"] == "agent_name"


@mock_aws
def test_get_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    resp = client.get_agent(agentId=agent["agent"]["agentId"])
    assert resp["agent"]["agentName"] == "testname"


@mock_aws
def test_get_agent_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    with pytest.raises(ClientError) as e:
        client.get_agent(agentId="non-existent-agent-id")
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_agents():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_agent(
        agentName="testname1",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    client.create_agent(
        agentName="testname2",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    resp = client.list_agents()
    # assert resp['agent']['agentName'] == "testname"

    assert len(resp["agentSummaries"]) == 2
    assert resp["agentSummaries"][0]["agentName"] == "testname1"
    assert resp["agentSummaries"][1]["agentName"] == "testname2"


@mock_aws
def test_delete_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
        tags={"Key": "test-tag-key"},
    )
    agent_id = agent["agent"]["agentId"]
    resp = client.delete_agent(agentId=agent_id, skipResourceInUseCheck=True)

    assert resp["agentId"] == agent_id
    assert resp["agentStatus"] == "DELETING"


@mock_aws
def test_create_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    resp = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )

    assert resp["knowledgeBase"]["name"] == "testkb"


@mock_aws
def test_list_knowledge_bases():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_knowledge_base(
        name="testkb1",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    client.create_knowledge_base(
        name="testkb2",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    resp = client.list_knowledge_bases()

    assert len(resp["knowledgeBaseSummaries"]) == 2
    assert resp["knowledgeBaseSummaries"][0]["name"] == "testkb1"
    assert resp["knowledgeBaseSummaries"][1]["name"] == "testkb2"


@mock_aws
def test_delete_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
    resp = client.delete_knowledge_base(knowledgeBaseId=kb_id)
    assert resp["knowledgeBaseId"] == kb_id
    assert resp["status"] == "DELETING"


@mock_aws
def test_delete_knowledge_base_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    with pytest.raises(ClientError) as e:
        client.delete_knowledge_base(knowledgeBaseId="non-existent-kb-id")
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_get_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
    resp = client.get_knowledge_base(knowledgeBaseId=kb_id)
    assert resp["knowledgeBase"]["name"] == "testkb"


@mock_aws
def test_get_knowledge_base_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    with pytest.raises(ClientError) as e:
        client.get_knowledge_base(knowledgeBaseId="non-existent-kb-id")
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_tag_resource_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
    )
    agent_arn = agent["agent"]["agentArn"]
    resp = client.tag_resource(resourceArn=agent_arn, tags={"Key": "test-tag"})
    resp = client.list_tags_for_resource(resourceArn=agent_arn)
    assert resp["tags"]["Key"] == "test-tag"


@mock_aws
def test_tag_resource_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
    )
    kb_arn = kb["knowledgeBase"]["knowledgeBaseArn"]
    resp = client.tag_resource(resourceArn=kb_arn, tags={"Key": "test-tag"})
    resp = client.list_tags_for_resource(resourceArn=kb_arn)
    assert resp["tags"]["Key"] == "test-tag"


@mock_aws
def test_untag_resource_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
    )
    agent_arn = agent["agent"]["agentArn"]
    resp = client.tag_resource(
        resourceArn=agent_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    resp = client.untag_resource(resourceArn=agent_arn, tagKeys=["Key1"])
    resp = client.list_tags_for_resource(resourceArn=agent_arn)
    assert len(resp["tags"]) == 1
    assert resp["tags"]["Key2"] == "test-tag2"


@mock_aws
def test_untag_resource_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
    )
    kb_arn = kb["knowledgeBase"]["knowledgeBaseArn"]
    resp = client.tag_resource(
        resourceArn=kb_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    resp = client.untag_resource(resourceArn=kb_arn, tagKeys=["Key1", "Key2"])
    resp = client.list_tags_for_resource(resourceArn=kb_arn)
    assert len(resp["tags"]) == 0


@mock_aws
def test_list_tags_for_resource_agent():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
    )
    agent_arn = agent["agent"]["agentArn"]
    resp = client.tag_resource(
        resourceArn=agent_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    resp = client.list_tags_for_resource(resourceArn=agent_arn)
    assert resp["tags"]["Key1"] == "test-tag"
    assert resp["tags"]["Key2"] == "test-tag2"


@mock_aws
def test_list_tags_for_resource_knowledge_base():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
    )
    kb_arn = kb["knowledgeBase"]["knowledgeBaseArn"]
    resp = client.tag_resource(
        resourceArn=kb_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    resp = client.list_tags_for_resource(resourceArn=kb_arn)
    assert resp["tags"]["Key1"] == "test-tag"
    assert resp["tags"]["Key2"] == "test-tag2"


@mock_aws
def test_create_knowledge_base_bad_knowledge_base_config():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as e:
        client.create_knowledge_base(
            name="testkb",
            description="description",
            roleArn="test_role_arn",
            knowledgeBaseConfiguration={
                "type": "vECTOR",
            },
            storageConfiguration={
                "type": "OPENSEARCH_SERVERLESS",
            },
            tags={"Key": "test-tag"},
        )
    assert e.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_create_knowledge_base_bad_storage_config():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    with pytest.raises(ClientError) as e:
        client.create_knowledge_base(
            name="testkb",
            description="description",
            roleArn="test_role_arn",
            knowledgeBaseConfiguration={
                "type": "VECTOR",
            },
            storageConfiguration={
                "type": "oPENSEARCH_SERVERLES",
            },
            tags={"Key": "test-tag"},
        )
    assert e.value.response["Error"]["Code"] == "ValidationException"


# @mock_aws
# def test_list_agents_token():
#     client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
#     client.create_agent(
#         agentName="testname1",
#         agentResourceRoleArn="test-agent-arn",
#         tags={
#             "Key": "test-tag-key",
#         },
#     )
#     client.create_agent(
#         agentName="testname2",
#         agentResourceRoleArn="test-agent-arn",
#         tags={
#             "Key": "test-tag-key",
#         },
#     )
#     resp = client.list_agents(nextToken="1")

#     assert len(resp["agentSummaries"]) == 1
#     assert resp["agentSummaries"][0]["agentName"] == "testname2"


# @mock_aws
# def test_list_agents_bad_token():
#     client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
#     client.create_agent(
#         agentName="testname1",
#         agentResourceRoleArn="test-agent-arn",
#         tags={
#             "Key": "test-tag-key",
#         },
#     )
#     client.create_agent(
#         agentName="testname2",
#         agentResourceRoleArn="test-agent-arn",
#         tags={
#             "Key": "test-tag-key",
#         },
#     )
#     with pytest.raises(ClientError) as e:
#         client.list_agents(nextToken="3")
#     assert e.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_list_agents_max_results():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_agent(
        agentName="testname1",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    client.create_agent(
        agentName="testname2",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )

    resp = client.list_agents(maxResults=1)

    assert len(resp["agentSummaries"]) == 1
    assert resp["agentSummaries"][0]["agentName"] == "testname1"


@mock_aws
def test_list_agents_big_max_results():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_agent(
        agentName="testname1",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )
    client.create_agent(
        agentName="testname2",
        agentResourceRoleArn="test-agent-arn",
        tags={
            "Key": "test-tag-key",
        },
    )

    resp = client.list_agents(maxResults=4)

    assert len(resp["agentSummaries"]) == 2
    assert resp["agentSummaries"][0]["agentName"] == "testname1"
    assert resp["agentSummaries"][1]["agentName"] == "testname2"


@mock_aws
def test_delete_agent_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
        tags={"Key": "test-tag-key"},
    )
    with pytest.raises(ClientError) as e:
        client.delete_agent(
            agentId="non-existent-agent-id", skipResourceInUseCheck=True
        )
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


# @mock_aws
# def test_delete_agent_in_use():
#     client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
#     agent = client.create_agent(
#         agentName="testname",
#         agentResourceRoleArn="test-agent-arn",
#         tags={"Key": "test-tag-key"},
#     )
#     agent_id = agent["agent"]["agentId"]
#     with patch("moto.bedrockagent.models.Agent.agent_status", return_value="IN_USE"):
#         # mock = Mock(spec = Agent)
#         # mock.agent_status.return_value = "IN_USE"
#         with pytest.raises(ClientError) as e:
#             resp = client.delete_agent(agentId=agent_id, skipResourceInUseCheck=False)
#         assert e.value.response["Error"]["Code"] == "ConflictException"


# @mock_aws
# def test_list_knowledge_bases_token():
#     client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
#     resp = client.create_knowledge_base(
#         name="testkb",
#         description="description",
#         roleArn="test_role_arn",
#         knowledgeBaseConfiguration={
#             "type": "VECTOR",
#         },
#         storageConfiguration={
#             "type": "OPENSEARCH_SERVERLESS",
#         },
#         tags={"Key": "test-tag"},
#     )
#     resp = client.create_knowledge_base(
#         name="testkb2",
#         description="description",
#         roleArn="test_role_arn",
#         knowledgeBaseConfiguration={
#             "type": "VECTOR",
#         },
#         storageConfiguration={
#             "type": "OPENSEARCH_SERVERLESS",
#         },
#         tags={"Key": "test-tag"},
#     )
#     resp = client.list_knowledge_bases(nextToken="1")

#     assert len(resp["knowledgeBaseSummaries"]) == 1
#     assert resp["knowledgeBaseSummaries"][0]["name"] == "testkb2"


# @mock_aws
# def test_list_knowledge_bases_bad_token():
#     client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
#     client.create_knowledge_base(
#         name="testkb",
#         description="description",
#         roleArn="test_role_arn",
#         knowledgeBaseConfiguration={
#             "type": "VECTOR",
#         },
#         storageConfiguration={
#             "type": "OPENSEARCH_SERVERLESS",
#         },
#         tags={"Key": "test-tag"},
#     )
#     client.create_knowledge_base(
#         name="testkb2",
#         description="description",
#         roleArn="test_role_arn",
#         knowledgeBaseConfiguration={
#             "type": "VECTOR",
#         },
#         storageConfiguration={
#             "type": "OPENSEARCH_SERVERLESS",
#         },
#         tags={"Key": "test-tag"},
#     )
#     with pytest.raises(ClientError) as e:
#         client.list_knowledge_bases(nextToken="3")
#     assert e.value.response["Error"]["Code"] == "ValidationException"


@mock_aws
def test_list_knowledge_bases_max_results():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    resp = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    resp = client.create_knowledge_base(
        name="testkb2",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )

    resp = client.list_knowledge_bases(maxResults=1)

    assert len(resp["knowledgeBaseSummaries"]) == 1
    assert resp["knowledgeBaseSummaries"][0]["name"] == "testkb"


@mock_aws
def test_list_knowledge_bases_big_max_results():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    resp = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )
    resp = client.create_knowledge_base(
        name="testkb2",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
        tags={"Key": "test-tag"},
    )

    resp = client.list_knowledge_bases(maxResults=4)

    assert len(resp["knowledgeBaseSummaries"]) == 2
    assert resp["knowledgeBaseSummaries"][0]["name"] == "testkb"
    assert resp["knowledgeBaseSummaries"][1]["name"] == "testkb2"


@mock_aws
def test_tag_resource_knowledge_base_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    kb = client.create_knowledge_base(
        name="testkb",
        description="description",
        roleArn="test_role_arn",
        knowledgeBaseConfiguration={
            "type": "VECTOR",
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
        },
    )
    kb_arn = kb["knowledgeBase"]["knowledgeBaseArn"]
    with pytest.raises(ClientError) as e:
        client.tag_resource(resourceArn=kb_arn + "no", tags={"Key": "test-tag"})
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_untag_resource_agent_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
    )
    agent_arn = agent["agent"]["agentArn"]
    client.tag_resource(
        resourceArn=agent_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    with pytest.raises(ClientError) as e:
        client.untag_resource(resourceArn=agent_arn + "no", tagKeys=["Key1"])
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"


@mock_aws
def test_list_tags_for_resource_agent_not_found():
    client = boto3.client("bedrock-agent", region_name=DEFAULT_REGION)
    agent = client.create_agent(
        agentName="testname",
        agentResourceRoleArn="test-agent-arn",
    )
    agent_arn = agent["agent"]["agentArn"]
    client.tag_resource(
        resourceArn=agent_arn, tags={"Key1": "test-tag", "Key2": "test-tag2"}
    )
    with pytest.raises(ClientError) as e:
        client.list_tags_for_resource(resourceArn=agent_arn + "no")
    assert e.value.response["Error"]["Code"] == "ResourceNotFoundException"
