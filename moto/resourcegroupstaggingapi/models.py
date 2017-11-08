from __future__ import unicode_literals
import boto3
from moto.core import BaseBackend, BaseModel


class ResourceGroupsTaggingAPIBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(ResourceGroupsTaggingAPIBackend, self).__init__()
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def get_resources(self, pagination_token, tag_filters, resources_per_page, tags_per_page, resource_type_filters):
        # implement here
        return pagination_token, resource_tag_mapping_list
    
    def get_tag_keys(self, pagination_token):
        # implement here
        return pagination_token, tag_keys
    
    def get_tag_values(self, pagination_token, key):
        # implement here
        return pagination_token, tag_values
    
    def tag_resources(self, resource_arn_list, tags):
        # implement here
        return failed_resources_map
    
    def untag_resources(self, resource_arn_list, tag_keys):
        # implement here
        return failed_resources_map
    
    # add methods from here


available_regions = boto3.session.Session().get_available_regions("resourcegroupstaggingapi")
resourcegroupstaggingapi_backends = {region: ResourceGroupsTaggingAPIBackend(region) for region in available_regions}
