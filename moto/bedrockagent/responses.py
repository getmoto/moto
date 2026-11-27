"""Handles incoming bedrockagent requests, invokes methods, returns responses."""

import json

from moto.core.responses import BaseResponse

from .models import AgentsforBedrockBackend, bedrockagent_backends


class AgentsforBedrockResponse(BaseResponse):
    """Handler for AgentsforBedrock requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="bedrock-agent")
        self.automated_parameter_parsing = True

    @property
    def bedrockagent_backend(self) -> AgentsforBedrockBackend:
        """Return backend instance specific for this region."""
        return bedrockagent_backends[self.current_account][self.region]

    def create_agent(self) -> str:
        agent_name = self._get_param("agentName")
        client_token = self._get_param("clientToken")
        instruction = self._get_param("instruction")
        foundation_model = self._get_param("foundationModel")
        description = self._get_param("description")
        idle_session_ttl_in_seconds = self._get_param("idleSessionTTLInSeconds")
        agent_resource_role_arn = self._get_param("agentResourceRoleArn")
        customer_encryption_key_arn = self._get_param("customerEncryptionKeyArn")
        tags = self._get_param("tags")
        prompt_override_configuration = self._get_param("promptOverrideConfiguration")
        agent = self.bedrockagent_backend.create_agent(
            agent_name=agent_name,
            client_token=client_token,
            instruction=instruction,
            foundation_model=foundation_model,
            description=description,
            idle_session_ttl_in_seconds=idle_session_ttl_in_seconds,
            agent_resource_role_arn=agent_resource_role_arn,
            customer_encryption_key_arn=customer_encryption_key_arn,
            tags=tags,
            prompt_override_configuration=prompt_override_configuration,
        )
        return json.dumps({"agent": dict(agent.to_dict())})

    def get_agent(self) -> str:
        agent_id = self._get_param("agentId")
        agent = self.bedrockagent_backend.get_agent(agent_id=agent_id)
        return json.dumps({"agent": dict(agent.to_dict())})

    def list_agents(self) -> str:
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        agents, next_token = self.bedrockagent_backend.list_agents(
            max_results=max_results,
            next_token=next_token,
        )
        return json.dumps(
            {
                "agentSummaries": [a.dict_summary() for a in agents],
                "nextToken": next_token,
            }
        )

    def delete_agent(self) -> str:
        skip_resource_in_use_check = self._get_bool_param("skipResourceInUseCheck")
        agent_id = self._get_param("agentId")
        agent_id, agent_status = self.bedrockagent_backend.delete_agent(
            agent_id=agent_id, skip_resource_in_use_check=skip_resource_in_use_check
        )
        return json.dumps({"agentId": agent_id, "agentStatus": agent_status})

    def create_knowledge_base(self) -> str:
        client_token = self._get_param("clientToken")
        name = self._get_param("name")
        description = self._get_param("description")
        role_arn = self._get_param("roleArn")
        knowledge_base_configuration = self._get_param("knowledgeBaseConfiguration")
        storage_configuration = self._get_param("storageConfiguration")
        tags = self._get_param("tags")
        knowledge_base = self.bedrockagent_backend.create_knowledge_base(
            client_token=client_token,
            name=name,
            description=description,
            role_arn=role_arn,
            knowledge_base_configuration=knowledge_base_configuration,
            storage_configuration=storage_configuration,
            tags=tags,
        )
        return json.dumps({"knowledgeBase": dict(knowledge_base.to_dict())})

    def list_knowledge_bases(self) -> str:
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        knowledge_bases, next_token = self.bedrockagent_backend.list_knowledge_bases(
            max_results=max_results,
            next_token=next_token,
        )
        return json.dumps(
            {
                "knowledgeBaseSummaries": [kb.dict_summary() for kb in knowledge_bases],
                "nextToken": next_token,
            }
        )

    def delete_knowledge_base(self) -> str:
        knowledge_base_id = self._get_param("knowledgeBaseId")
        (
            knowledge_base_id,
            knowledge_base_status,
        ) = self.bedrockagent_backend.delete_knowledge_base(
            knowledge_base_id=knowledge_base_id
        )
        return json.dumps(
            {"knowledgeBaseId": knowledge_base_id, "status": knowledge_base_status}
        )

    def get_knowledge_base(self) -> str:
        knowledge_base_id = self._get_param("knowledgeBaseId")
        knowledge_base = self.bedrockagent_backend.get_knowledge_base(
            knowledge_base_id=knowledge_base_id
        )
        return json.dumps({"knowledgeBase": knowledge_base.to_dict()})

    def tag_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tags = self._get_param("tags")
        self.bedrockagent_backend.tag_resource(resource_arn=resource_arn, tags=tags)
        return json.dumps({})

    def untag_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.bedrockagent_backend.untag_resource(
            resource_arn=resource_arn, tag_keys=tag_keys
        )
        return json.dumps({})

    def list_tags_for_resource(self) -> str:
        resource_arn = self._get_param("resourceArn")
        tags = self.bedrockagent_backend.list_tags_for_resource(
            resource_arn=resource_arn
        )
        return json.dumps({"tags": tags})
