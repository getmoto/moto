from moto.core.responses import ActionResult, BaseResponse, EmptyResult

from .models import DevOpsAgentBackend, devopsagent_backends


class DevOpsAgentResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="devops-agent")
        self.automated_parameter_parsing = True

    @property
    def backend(self) -> DevOpsAgentBackend:
        return devopsagent_backends[self.current_account][self.region]

    def create_agent_space(self) -> ActionResult:
        params = self._get_params()
        tags = params.get("tags")
        space = self.backend.create_agent_space(
            name=params["name"],
            description=params.get("description"),
            locale=params.get("locale"),
            kms_key_arn=params.get("kmsKeyArn"),
            tags=tags,
        )
        result = {"agentSpace": space.to_dict()}
        if tags:
            result["tags"] = tags
        return ActionResult(result)

    def get_agent_space(self) -> ActionResult:
        agent_space_id = self._get_param("agentSpaceId")
        space = self.backend.get_agent_space(agent_space_id)
        tags = self.backend.list_tags_for_resource(space.arn)
        result = {"agentSpace": space.to_dict()}
        if tags:
            result["tags"] = tags
        return ActionResult(result)

    def list_agent_spaces(self) -> ActionResult:
        spaces = self.backend.list_agent_spaces()
        return ActionResult(
            {"agentSpaces": [s.to_dict() for s in spaces]}
        )

    def update_agent_space(self) -> ActionResult:
        agent_space_id = self._get_param("agentSpaceId")
        params = self._get_params()
        space = self.backend.update_agent_space(
            agent_space_id=agent_space_id,
            name=params.get("name"),
            description=params.get("description"),
            locale=params.get("locale"),
        )
        return ActionResult({"agentSpace": space.to_dict()})

    def delete_agent_space(self) -> ActionResult:
        agent_space_id = self._get_param("agentSpaceId")
        self.backend.delete_agent_space(agent_space_id)
        return EmptyResult()

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        params = self._get_params()
        self.backend.tag_resource(resource_arn, params["tags"])
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.backend.untag_resource(resource_arn, tag_keys)
        return EmptyResult()

    def list_tags_for_resource(self) -> ActionResult:
        resource_arn = self._get_param("resourceArn")
        tags = self.backend.list_tags_for_resource(resource_arn)
        return ActionResult({"tags": tags})
