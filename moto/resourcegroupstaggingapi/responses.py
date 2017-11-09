from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import resourcegroupstaggingapi_backends
import json


class ResourceGroupsTaggingAPIResponse(BaseResponse):
    SERVICE_NAME = 'resourcegroupstaggingapi'

    @property
    def backend(self):
        """
        Backend
        :returns: Resource tagging api backend
        :rtype: moto.resourcegroupstaggingapi.models.ResourceGroupsTaggingAPIBackend
        """
        return resourcegroupstaggingapi_backends[self.region]

    def get_resources(self):
        pagination_token = self._get_param("PaginationToken")
        tag_filters = self._get_list_prefix("TagFilters.member")
        resources_per_page = self._get_int_param("ResourcesPerPage", 50)
        tags_per_page = self._get_int_param("TagsPerPage", 100)
        resource_type_filters = self._get_list_prefix("ResourceTypeFilters.member")

        pagination_token, resource_tag_mapping_list = self.backend.get_resources(
            pagination_token=pagination_token,
            tag_filters=tag_filters,
            resources_per_page=resources_per_page,
            tags_per_page=tags_per_page,
            resource_type_filters=resource_type_filters,
        )

        # Format tag response
        response = {
            'ResourceTagMappingList': resource_tag_mapping_list
        }
        if pagination_token:
            response['PaginationToken'] = pagination_token

        return json.dumps(response)

    def get_tag_keys(self):
        pagination_token = self._get_param("PaginationToken")
        pagination_token, tag_keys = self.backend.get_tag_keys(
            pagination_token=pagination_token,
        )
        # TODO: adjust response
        return json.dumps(dict(paginationToken=pagination_token, tagKeys=tag_keys))

    def get_tag_values(self):
        pagination_token = self._get_param("PaginationToken")
        key = self._get_param("Key")
        pagination_token, tag_values = self.backend.get_tag_values(
            pagination_token=pagination_token,
            key=key,
        )
        # TODO: adjust response
        return json.dumps(dict(paginationToken=pagination_token, tagValues=tag_values))

    def tag_resources(self):
        resource_arn_list = self._get_list_prefix("ResourceARNList.member")
        tags = self._get_param("Tags")
        failed_resources_map = self.backend.tag_resources(
            resource_arn_list=resource_arn_list,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict(failedResourcesMap=failed_resources_map))

    def untag_resources(self):
        resource_arn_list = self._get_list_prefix("ResourceARNList.member")
        tag_keys = self._get_list_prefix("TagKeys.member")
        failed_resources_map = self.backend.untag_resources(
            resource_arn_list=resource_arn_list,
            tag_keys=tag_keys,
        )
        # TODO: adjust response
        return json.dumps(dict(failedResourcesMap=failed_resources_map))
