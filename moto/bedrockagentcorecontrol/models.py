"""BedrockAgentCoreControl models."""

from collections import OrderedDict
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import utcnow
from moto.moto_api._internal import mock_random
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition

from .exceptions import ConflictException, ResourceNotFoundException


class AgentRuntime(BaseModel, ManagedState):
    def __init__(
        self,
        region_name: str,
        account_id: str,
        agent_runtime_name: str,
        agent_runtime_artifact: dict[str, Any],
        role_arn: str,
        network_configuration: dict[str, Any],
        description: Optional[str],
        authorizer_configuration: Optional[dict[str, Any]],
        request_header_configuration: Optional[dict[str, Any]],
        protocol_configuration: Optional[dict[str, Any]],
        lifecycle_configuration: Optional[dict[str, Any]],
        environment_variables: Optional[dict[str, str]],
    ):
        ManagedState.__init__(
            self,
            "bedrock-agentcore-control::agent_runtime",
            transitions=[("CREATING", "READY")],
        )
        self.region_name = region_name
        self.account_id = account_id
        self.agent_runtime_id = (
            f"a{mock_random.get_random_hex(9)}-{mock_random.get_random_hex(10)}"
        )
        self.agent_runtime_version = "1"
        runtime_uuid = str(mock_random.uuid4())
        self.agent_runtime_arn = f"arn:{get_partition(region_name)}:bedrock-agentcore:{region_name}:{account_id}:agent/{runtime_uuid}:{self.agent_runtime_version}"
        self.agent_runtime_name = agent_runtime_name
        self.agent_runtime_artifact = agent_runtime_artifact
        self.role_arn = role_arn
        self.network_configuration = network_configuration
        self.description = description or ""
        self.authorizer_configuration = authorizer_configuration
        self.request_header_configuration = request_header_configuration
        self.protocol_configuration = protocol_configuration
        self.lifecycle_configuration = lifecycle_configuration or {}
        self.environment_variables = environment_variables
        now = utcnow()
        self.created_at = now
        self.last_updated_at = now
        self.workload_identity_details = {
            "workloadIdentityArn": f"arn:{get_partition(region_name)}:bedrock-agentcore:{region_name}:{account_id}:workload-identity-directory/default/workload-identity/{self.agent_runtime_id}"
        }
        # Store version snapshots for ListAgentRuntimeVersions
        self.versions: list[dict[str, Any]] = []
        self._snapshot_version()

    def _snapshot_version(self) -> None:
        self.versions.append(
            {
                "agentRuntimeArn": self.agent_runtime_arn,
                "agentRuntimeId": self.agent_runtime_id,
                "agentRuntimeVersion": self.agent_runtime_version,
                "agentRuntimeName": self.agent_runtime_name,
                "description": self.description,
                "lastUpdatedAt": self.last_updated_at,
                "status": self.status,
            }
        )

    def update(
        self,
        agent_runtime_artifact: dict[str, Any],
        role_arn: str,
        network_configuration: dict[str, Any],
        description: Optional[str],
        authorizer_configuration: Optional[dict[str, Any]],
        request_header_configuration: Optional[dict[str, Any]],
        protocol_configuration: Optional[dict[str, Any]],
        lifecycle_configuration: Optional[dict[str, Any]],
        environment_variables: Optional[dict[str, str]],
    ) -> None:
        self.agent_runtime_artifact = agent_runtime_artifact
        self.role_arn = role_arn
        self.network_configuration = network_configuration
        if description is not None:
            self.description = description
        if authorizer_configuration is not None:
            self.authorizer_configuration = authorizer_configuration
        if request_header_configuration is not None:
            self.request_header_configuration = request_header_configuration
        if protocol_configuration is not None:
            self.protocol_configuration = protocol_configuration
        if lifecycle_configuration is not None:
            self.lifecycle_configuration = lifecycle_configuration
        if environment_variables is not None:
            self.environment_variables = environment_variables
        new_version = str(int(self.agent_runtime_version) + 1)
        self.agent_runtime_version = new_version
        runtime_uuid = self.agent_runtime_arn.split("agent/")[1].split(":")[0]
        self.agent_runtime_arn = f"arn:{get_partition(self.region_name)}:bedrock-agentcore:{self.region_name}:{self.account_id}:agent/{runtime_uuid}:{new_version}"
        self.last_updated_at = utcnow()
        self.status = "UPDATING"
        self._snapshot_version()

    def to_summary(self) -> dict[str, Any]:
        return {
            "agentRuntimeArn": self.agent_runtime_arn,
            "agentRuntimeId": self.agent_runtime_id,
            "agentRuntimeVersion": self.agent_runtime_version,
            "agentRuntimeName": self.agent_runtime_name,
            "description": self.description,
            "lastUpdatedAt": self.last_updated_at,
            "status": self.status,
        }


class AgentRuntimeEndpoint(BaseModel, ManagedState):
    def __init__(
        self,
        region_name: str,
        account_id: str,
        agent_runtime: "AgentRuntime",
        name: str,
        agent_runtime_version: Optional[str],
        description: Optional[str],
    ):
        ManagedState.__init__(
            self,
            "bedrock-agentcore-control::agent_runtime_endpoint",
            transitions=[("CREATING", "READY")],
        )
        self.region_name = region_name
        self.account_id = account_id
        self.name = name
        self.endpoint_id = (
            f"e{mock_random.get_random_hex(9)}-{mock_random.get_random_hex(10)}"
        )
        endpoint_uuid = str(mock_random.uuid4())
        self.agent_runtime_endpoint_arn = f"arn:{get_partition(region_name)}:bedrock-agentcore:{region_name}:{account_id}:agentEndpoint/{endpoint_uuid}"
        self.agent_runtime_arn = agent_runtime.agent_runtime_arn
        self.agent_runtime_id = agent_runtime.agent_runtime_id
        self.target_version = (
            agent_runtime_version or agent_runtime.agent_runtime_version
        )
        self.live_version = self.target_version
        self.description = description or ""
        now = utcnow()
        self.created_at = now
        self.last_updated_at = now

    def update(
        self,
        agent_runtime_version: Optional[str],
        description: Optional[str],
    ) -> None:
        if agent_runtime_version is not None:
            self.target_version = agent_runtime_version
        if description is not None:
            self.description = description
        self.last_updated_at = utcnow()
        self.status = "UPDATING"

    def to_summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "agentRuntimeEndpointArn": self.agent_runtime_endpoint_arn,
            "agentRuntimeArn": self.agent_runtime_arn,
            "status": self.status,
            "id": self.endpoint_id,
            "description": self.description,
            "createdAt": self.created_at,
            "lastUpdatedAt": self.last_updated_at,
        }


class BedrockAgentCoreControlBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.agent_runtimes: dict[str, AgentRuntime] = OrderedDict()
        # endpoints keyed by (agent_runtime_id, endpoint_name)
        self.agent_runtime_endpoints: dict[tuple[str, str], AgentRuntimeEndpoint] = (
            OrderedDict()
        )
        self.tagger = TaggingService()

    def _get_runtime(self, agent_runtime_id: str) -> AgentRuntime:
        if agent_runtime_id not in self.agent_runtimes:
            raise ResourceNotFoundException(
                f"Could not find Agent Runtime with ID {agent_runtime_id}"
            )
        return self.agent_runtimes[agent_runtime_id]

    def create_agent_runtime(
        self,
        agent_runtime_name: str,
        agent_runtime_artifact: dict[str, Any],
        role_arn: str,
        network_configuration: dict[str, Any],
        description: Optional[str],
        authorizer_configuration: Optional[dict[str, Any]],
        request_header_configuration: Optional[dict[str, Any]],
        protocol_configuration: Optional[dict[str, Any]],
        lifecycle_configuration: Optional[dict[str, Any]],
        environment_variables: Optional[dict[str, str]],
        tags: Optional[dict[str, str]],
    ) -> AgentRuntime:
        runtime = AgentRuntime(
            region_name=self.region_name,
            account_id=self.account_id,
            agent_runtime_name=agent_runtime_name,
            agent_runtime_artifact=agent_runtime_artifact,
            role_arn=role_arn,
            network_configuration=network_configuration,
            description=description,
            authorizer_configuration=authorizer_configuration,
            request_header_configuration=request_header_configuration,
            protocol_configuration=protocol_configuration,
            lifecycle_configuration=lifecycle_configuration,
            environment_variables=environment_variables,
        )
        self.agent_runtimes[runtime.agent_runtime_id] = runtime
        if tags:
            self.tagger.tag_resource(
                runtime.agent_runtime_arn,
                [{"Key": k, "Value": v} for k, v in tags.items()],
            )
        return runtime

    def get_agent_runtime(self, agent_runtime_id: str) -> AgentRuntime:
        runtime = self._get_runtime(agent_runtime_id)
        runtime.advance()
        return runtime

    def update_agent_runtime(
        self,
        agent_runtime_id: str,
        agent_runtime_artifact: dict[str, Any],
        role_arn: str,
        network_configuration: dict[str, Any],
        description: Optional[str],
        authorizer_configuration: Optional[dict[str, Any]],
        request_header_configuration: Optional[dict[str, Any]],
        protocol_configuration: Optional[dict[str, Any]],
        lifecycle_configuration: Optional[dict[str, Any]],
        environment_variables: Optional[dict[str, str]],
    ) -> AgentRuntime:
        runtime = self._get_runtime(agent_runtime_id)
        runtime.update(
            agent_runtime_artifact=agent_runtime_artifact,
            role_arn=role_arn,
            network_configuration=network_configuration,
            description=description,
            authorizer_configuration=authorizer_configuration,
            request_header_configuration=request_header_configuration,
            protocol_configuration=protocol_configuration,
            lifecycle_configuration=lifecycle_configuration,
            environment_variables=environment_variables,
        )
        return runtime

    def delete_agent_runtime(self, agent_runtime_id: str) -> AgentRuntime:
        runtime = self._get_runtime(agent_runtime_id)
        # Remove all endpoints for this runtime
        keys_to_remove = [
            k for k in self.agent_runtime_endpoints if k[0] == agent_runtime_id
        ]
        for key in keys_to_remove:
            self.agent_runtime_endpoints.pop(key)
        self.agent_runtimes.pop(agent_runtime_id)
        return runtime

    def list_agent_runtimes(self) -> list[AgentRuntime]:
        return list(self.agent_runtimes.values())

    def list_agent_runtime_versions(
        self, agent_runtime_id: str
    ) -> list[dict[str, Any]]:
        runtime = self._get_runtime(agent_runtime_id)
        return list(reversed(runtime.versions))

    def create_agent_runtime_endpoint(
        self,
        agent_runtime_id: str,
        name: str,
        agent_runtime_version: Optional[str],
        description: Optional[str],
        tags: Optional[dict[str, str]],
    ) -> AgentRuntimeEndpoint:
        runtime = self._get_runtime(agent_runtime_id)
        key = (agent_runtime_id, name)
        if key in self.agent_runtime_endpoints:
            raise ConflictException(
                f"Endpoint {name} already exists for Agent Runtime {agent_runtime_id}"
            )
        endpoint = AgentRuntimeEndpoint(
            region_name=self.region_name,
            account_id=self.account_id,
            agent_runtime=runtime,
            name=name,
            agent_runtime_version=agent_runtime_version,
            description=description,
        )
        self.agent_runtime_endpoints[key] = endpoint
        if tags:
            self.tagger.tag_resource(
                endpoint.agent_runtime_endpoint_arn,
                [{"Key": k, "Value": v} for k, v in tags.items()],
            )
        return endpoint

    def get_agent_runtime_endpoint(
        self, agent_runtime_id: str, endpoint_name: str
    ) -> AgentRuntimeEndpoint:
        key = (agent_runtime_id, endpoint_name)
        if key not in self.agent_runtime_endpoints:
            raise ResourceNotFoundException(
                f"Could not find endpoint {endpoint_name} for Agent Runtime {agent_runtime_id}"
            )
        endpoint = self.agent_runtime_endpoints[key]
        endpoint.advance()
        return endpoint

    def update_agent_runtime_endpoint(
        self,
        agent_runtime_id: str,
        endpoint_name: str,
        agent_runtime_version: Optional[str],
        description: Optional[str],
    ) -> AgentRuntimeEndpoint:
        endpoint = self.get_agent_runtime_endpoint(agent_runtime_id, endpoint_name)
        endpoint.update(
            agent_runtime_version=agent_runtime_version,
            description=description,
        )
        return endpoint

    def delete_agent_runtime_endpoint(
        self, agent_runtime_id: str, endpoint_name: str
    ) -> AgentRuntimeEndpoint:
        endpoint = self.get_agent_runtime_endpoint(agent_runtime_id, endpoint_name)
        key = (agent_runtime_id, endpoint_name)
        self.agent_runtime_endpoints.pop(key)
        return endpoint

    def list_agent_runtime_endpoints(
        self, agent_runtime_id: str
    ) -> list[AgentRuntimeEndpoint]:
        self._get_runtime(agent_runtime_id)
        return [
            ep
            for (rid, _), ep in self.agent_runtime_endpoints.items()
            if rid == agent_runtime_id
        ]

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, [{"Key": k, "Value": v} for k, v in tags.items()]
        )

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)


bedrockagentcorecontrol_backends = BackendDict(
    BedrockAgentCoreControlBackend,
    "bedrock-agentcore-control",
    # botocore does not yet include endpoint data for this service
    use_boto3_regions=False,
    additional_regions=[
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "ap-south-1",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-north-1",
        "sa-east-1",
    ],
)
