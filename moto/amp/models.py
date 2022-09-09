"""PrometheusServiceBackend class with methods for supported APIs."""

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict, unix_time
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService
from typing import Dict
from uuid import uuid4
from .exceptions import RuleGroupNamespaceNotFound, WorkspaceNotFound
from .utils import PAGINATION_MODEL


class RuleGroupNamespace(BaseModel):
    def __init__(self, account_id, region, workspace_id, name, data, tag_fn):
        self.name = name
        self.data = data
        self.tag_fn = tag_fn
        self.arn = f"arn:aws:aps:{region}:{account_id}:rulegroupsnamespace/{workspace_id}/{self.name}"
        self.created_at = unix_time()
        self.modified_at = self.created_at

    def update(self, new_data):
        self.data = new_data
        self.modified_at = unix_time()

    def to_dict(self):
        return {
            "name": self.name,
            "arn": self.arn,
            "status": {"statusCode": "ACTIVE"},
            "createdAt": self.created_at,
            "modifiedAt": self.modified_at,
            "data": self.data,
            "tags": self.tag_fn(self.arn),
        }


class Workspace(BaseModel):
    def __init__(self, account_id, region, alias, tag_fn):
        self.alias = alias
        self.workspace_id = f"ws-{uuid4()}"
        self.arn = f"arn:aws:aps:{region}:{account_id}:workspace/{self.workspace_id}"
        self.endpoint = f"https://aps-workspaces.{region}.amazonaws.com/workspaces/{self.workspace_id}/"
        self.status = {"statusCode": "ACTIVE"}
        self.created_at = unix_time()
        self.tag_fn = tag_fn
        self.rule_group_namespaces = dict()

    def to_dict(self):
        return {
            "alias": self.alias,
            "arn": self.arn,
            "workspaceId": self.workspace_id,
            "status": self.status,
            "createdAt": self.created_at,
            "prometheusEndpoint": self.endpoint,
            "tags": self.tag_fn(self.arn),
        }


class PrometheusServiceBackend(BaseBackend):
    """Implementation of PrometheusService APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.workspaces: Dict(str, Workspace) = dict()
        self.tagger = TaggingService()

    def create_workspace(self, alias, tags):
        """
        The ClientToken-parameter is not yet implemented
        """
        workspace = Workspace(
            self.account_id,
            self.region_name,
            alias=alias,
            tag_fn=self.list_tags_for_resource,
        )
        self.workspaces[workspace.workspace_id] = workspace
        self.tag_resource(workspace.arn, tags)
        return workspace

    def describe_workspace(self, workspace_id) -> Workspace:
        if workspace_id not in self.workspaces:
            raise WorkspaceNotFound(workspace_id)
        return self.workspaces[workspace_id]

    def list_tags_for_resource(self, resource_arn):
        return self.tagger.get_tag_dict_for_resource(resource_arn)

    def update_workspace_alias(self, alias, workspace_id):
        """
        The ClientToken-parameter is not yet implemented
        """
        self.workspaces[workspace_id].alias = alias

    def delete_workspace(self, workspace_id):
        """
        The ClientToken-parameter is not yet implemented
        """
        self.workspaces.pop(workspace_id, None)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_workspaces(self, alias):
        if alias:
            return [w for w in self.workspaces.values() if w.alias == alias]
        return list(self.workspaces.values())

    def tag_resource(self, resource_arn, tags):
        tags = self.tagger.convert_dict_to_tags_input(tags)
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn, tag_keys):
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def create_rule_groups_namespace(
        self, data, name, tags, workspace_id
    ) -> RuleGroupNamespace:
        """
        The ClientToken-parameter is not yet implemented
        """
        workspace = self.describe_workspace(workspace_id)
        group = RuleGroupNamespace(
            account_id=self.account_id,
            region=self.region_name,
            workspace_id=workspace_id,
            name=name,
            data=data,
            tag_fn=self.list_tags_for_resource,
        )
        workspace.rule_group_namespaces[name] = group
        self.tag_resource(group.arn, tags)
        return group

    def delete_rule_groups_namespace(self, name, workspace_id) -> None:
        """
        The ClientToken-parameter is not yet implemented
        """
        ws = self.describe_workspace(workspace_id)
        ws.rule_group_namespaces.pop(name, None)

    def describe_rule_groups_namespace(self, name, workspace_id) -> RuleGroupNamespace:
        ws = self.describe_workspace(workspace_id)
        if name not in ws.rule_group_namespaces:
            raise RuleGroupNamespaceNotFound(name=name)
        return ws.rule_group_namespaces[name]

    def put_rule_groups_namespace(self, data, name, workspace_id) -> RuleGroupNamespace:
        """
        The ClientToken-parameter is not yet implemented
        """
        ns = self.describe_rule_groups_namespace(name=name, workspace_id=workspace_id)
        ns.update(data)
        return ns

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_rule_groups_namespaces(self, name, workspace_id):
        ws = self.describe_workspace(workspace_id)
        if name:
            return [
                ns
                for ns_name, ns in ws.rule_group_namespaces.items()
                if ns_name.startswith(name)
            ]
        return list(ws.rule_group_namespaces.values())


amp_backends = BackendDict(PrometheusServiceBackend, "amp")
