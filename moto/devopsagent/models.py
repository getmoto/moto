from collections import OrderedDict
from typing import Any, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import utcnow
from moto.moto_api._internal import mock_random
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition

from .exceptions import ResourceNotFoundException


class AgentSpace(BaseModel):
    def __init__(
        self,
        region_name: str,
        account_id: str,
        name: str,
        description: Optional[str],
        locale: Optional[str],
        kms_key_arn: Optional[str],
    ):
        self.region_name = region_name
        self.account_id = account_id
        self.name = name
        self.description = description or ""
        self.locale = locale or ""
        self.kms_key_arn = kms_key_arn or ""
        self.agent_space_id = f"as-{mock_random.get_random_hex(12)}"
        self.arn = f"arn:{get_partition(region_name)}:aidevops:{region_name}:{account_id}:agentspace/{self.agent_space_id}"
        now = utcnow()
        self.created_at = now
        self.updated_at = now

    def update(
        self,
        name: Optional[str],
        description: Optional[str],
        locale: Optional[str],
    ) -> None:
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if locale is not None:
            self.locale = locale
        self.updated_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "agentSpaceId": self.agent_space_id,
            "name": self.name,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.description:
            result["description"] = self.description
        if self.locale:
            result["locale"] = self.locale
        if self.kms_key_arn:
            result["kmsKeyArn"] = self.kms_key_arn
        return result


class DevOpsAgentBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.agent_spaces: OrderedDict[str, AgentSpace] = OrderedDict()
        self.tagger = TaggingService()

    def create_agent_space(
        self,
        name: str,
        description: Optional[str],
        locale: Optional[str],
        kms_key_arn: Optional[str],
        tags: Optional[dict[str, str]],
    ) -> AgentSpace:
        space = AgentSpace(
            region_name=self.region_name,
            account_id=self.account_id,
            name=name,
            description=description,
            locale=locale,
            kms_key_arn=kms_key_arn,
        )
        self.agent_spaces[space.agent_space_id] = space
        if tags:
            self.tagger.tag_resource(
                space.arn,
                [{"Key": k, "Value": v} for k, v in tags.items()],
            )
        return space

    def get_agent_space(self, agent_space_id: str) -> AgentSpace:
        if agent_space_id not in self.agent_spaces:
            raise ResourceNotFoundException(
                f"Could not find AgentSpace with ID {agent_space_id}"
            )
        return self.agent_spaces[agent_space_id]

    def list_agent_spaces(self) -> list[AgentSpace]:
        return list(self.agent_spaces.values())

    def update_agent_space(
        self,
        agent_space_id: str,
        name: Optional[str],
        description: Optional[str],
        locale: Optional[str],
    ) -> AgentSpace:
        space = self.get_agent_space(agent_space_id)
        space.update(name=name, description=description, locale=locale)
        return space

    def delete_agent_space(self, agent_space_id: str) -> None:
        space = self.get_agent_space(agent_space_id)
        self.tagger.delete_all_tags_for_resource(space.arn)
        self.agent_spaces.pop(agent_space_id)

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, [{"Key": k, "Value": v} for k, v in tags.items()]
        )

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)


devopsagent_backends = BackendDict(
    DevOpsAgentBackend,
    "devops-agent",
    use_boto3_regions=False,
    additional_regions=[
        "us-east-1",
        "us-west-2",
        "ca-central-1",
        "sa-east-1",
        "ap-south-1",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-northeast-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
    ],
)
