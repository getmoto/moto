from __future__ import unicode_literals
import json

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from moto.core.responses import BaseResponse
from .models import resourcegroups_backends


class ResourceGroupsResponse(BaseResponse):
    SERVICE_NAME = "resource-groups"

    @property
    def resourcegroups_backend(self):
        return resourcegroups_backends[self.region]

    def create_group(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        resource_query = self._get_param("ResourceQuery")
        tags = self._get_param("Tags")
        configuration = self._get_param("Configuration")
        group = self.resourcegroups_backend.create_group(
            name=name,
            description=description,
            resource_query=resource_query,
            tags=tags,
            configuration=configuration,
        )
        return json.dumps(
            {
                "Group": {
                    "GroupArn": group.arn,
                    "Name": group.name,
                    "Description": group.description,
                },
                "ResourceQuery": group.resource_query,
                "Tags": group.tags,
                "GroupConfiguration": {"Configuration": group.configuration},
            }
        )

    def delete_group(self):
        group_name = self._get_param("GroupName") or self._get_param("Group")
        group = self.resourcegroups_backend.delete_group(group_name=group_name)
        return json.dumps(
            {
                "Group": {
                    "GroupArn": group.arn,
                    "Name": group.name,
                    "Description": group.description,
                }
            }
        )

    def get_group(self):
        group_name = self._get_param("GroupName")
        group = self.resourcegroups_backend.get_group(group_name=group_name)
        return json.dumps(
            {
                "Group": {
                    "GroupArn": group.arn,
                    "Name": group.name,
                    "Description": group.description,
                }
            }
        )

    def get_group_query(self):
        group_name = self._get_param("GroupName")
        group_arn = self._get_param("Group")
        if group_arn and not group_name:
            group_name = group_arn.split(":")[-1]
        group = self.resourcegroups_backend.get_group(group_name=group_name)
        return json.dumps(
            {
                "GroupQuery": {
                    "GroupName": group.name,
                    "ResourceQuery": group.resource_query,
                }
            }
        )

    def get_tags(self):
        arn = unquote(self._get_param("Arn"))
        return json.dumps(
            {"Arn": arn, "Tags": self.resourcegroups_backend.get_tags(arn=arn)}
        )

    def list_group_resources(self):
        raise NotImplementedError(
            "ResourceGroups.list_group_resources is not yet implemented"
        )

    def list_groups(self):
        filters = self._get_param("Filters")
        if filters:
            raise NotImplementedError(
                "ResourceGroups.list_groups with filter parameter is not yet implemented"
            )
        max_results = self._get_int_param("MaxResults", 50)
        next_token = self._get_param("NextToken")
        groups = self.resourcegroups_backend.list_groups(
            filters=filters, max_results=max_results, next_token=next_token
        )
        return json.dumps(
            {
                "GroupIdentifiers": [
                    {"GroupName": group.name, "GroupArn": group.arn}
                    for group in groups.values()
                ],
                "Groups": [
                    {
                        "GroupArn": group.arn,
                        "Name": group.name,
                        "Description": group.description,
                    }
                    for group in groups.values()
                ],
                "NextToken": next_token,
            }
        )

    def search_resources(self):
        raise NotImplementedError(
            "ResourceGroups.search_resources is not yet implemented"
        )

    def tag(self):
        arn = unquote(self._get_param("Arn"))
        tags = self._get_param("Tags")
        if arn not in self.resourcegroups_backend.groups.by_arn:
            raise NotImplementedError(
                "ResourceGroups.tag with non-resource-group Arn parameter is not yet implemented"
            )
        self.resourcegroups_backend.tag(arn=arn, tags=tags)
        return json.dumps({"Arn": arn, "Tags": tags})

    def untag(self):
        arn = unquote(self._get_param("Arn"))
        keys = self._get_param("Keys")
        if arn not in self.resourcegroups_backend.groups.by_arn:
            raise NotImplementedError(
                "ResourceGroups.untag with non-resource-group Arn parameter is not yet implemented"
            )
        self.resourcegroups_backend.untag(arn=arn, keys=keys)
        return json.dumps({"Arn": arn, "Keys": keys})

    def update_group(self):
        group_name = self._get_param("GroupName")
        description = self._get_param("Description", "")
        group = self.resourcegroups_backend.update_group(
            group_name=group_name, description=description
        )
        return json.dumps(
            {
                "Group": {
                    "GroupArn": group.arn,
                    "Name": group.name,
                    "Description": group.description,
                }
            }
        )

    def update_group_query(self):
        group_name = self._get_param("GroupName")
        resource_query = self._get_param("ResourceQuery")
        group_arn = self._get_param("Group")
        if group_arn and not group_name:
            group_name = group_arn.split(":")[-1]
        group = self.resourcegroups_backend.update_group_query(
            group_name=group_name, resource_query=resource_query
        )
        return json.dumps(
            {"GroupQuery": {"GroupName": group.name, "ResourceQuery": resource_query}}
        )

    def get_group_configuration(self):
        group_name = self._get_param("Group")
        configuration = self.resourcegroups_backend.get_group_configuration(
            group_name=group_name
        )
        return json.dumps({"GroupConfiguration": {"Configuration": configuration}})

    def put_group_configuration(self):
        group_name = self._get_param("Group")
        configuration = self._get_param("Configuration")
        self.resourcegroups_backend.put_group_configuration(
            group_name=group_name, configuration=configuration
        )
        return json.dumps({"GroupConfiguration": {"Configuration": configuration}})
