from __future__ import unicode_literals

from moto.core.responses import BaseResponse
from moto.ec2.models import validate_resource_ids
from moto.ec2.utils import filters_from_querystring
from moto.core.utils import tags_from_query_string


class TagResponse(BaseResponse):
    def create_tags(self):
        resource_ids = self._get_multi_param("ResourceId")
        validate_resource_ids(resource_ids)
        self.ec2_backend.do_resources_exist(resource_ids)
        tags = tags_from_query_string(self.querystring)
        if self.is_not_dryrun("CreateTags"):
            self.ec2_backend.create_tags(resource_ids, tags)
            return CREATE_RESPONSE

    def delete_tags(self):
        resource_ids = self._get_multi_param("ResourceId")
        validate_resource_ids(resource_ids)
        tags = tags_from_query_string(self.querystring)
        if self.is_not_dryrun("DeleteTags"):
            self.ec2_backend.delete_tags(resource_ids, tags)
            return DELETE_RESPONSE

    def describe_tags(self):
        filters = filters_from_querystring(querystring_dict=self.querystring)
        tags = self.ec2_backend.describe_tags(filters=filters)
        template = self.response_template(DESCRIBE_RESPONSE)
        return template.render(tags=tags)


CREATE_RESPONSE = """<CreateTagsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</CreateTagsResponse>"""

DELETE_RESPONSE = """<DeleteTagsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteTagsResponse>"""

DESCRIBE_RESPONSE = """<DescribeTagsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <tagSet>
      {% for tag in tags %}
          <item>
             <resourceId>{{ tag.resource_id }}</resourceId>
             <resourceType>{{ tag.resource_type }}</resourceType>
             <key>{{ tag.key }}</key>
             <value>{{ tag.value }}</value>
          </item>
      {% endfor %}
    </tagSet>
</DescribeTagsResponse>"""
