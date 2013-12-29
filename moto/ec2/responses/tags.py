from jinja2 import Template

from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.utils import resource_ids_from_querystring


class TagResponse(BaseResponse):

    def create_tags(self):
        resource_ids = resource_ids_from_querystring(self.querystring)
        for resource_id, tag in resource_ids.iteritems():
            ec2_backend.create_tag(resource_id, tag[0], tag[1])
        return CREATE_RESPONSE

    def delete_tags(self):
        resource_ids = resource_ids_from_querystring(self.querystring)
        for resource_id, tag in resource_ids.iteritems():
            ec2_backend.delete_tag(resource_id, tag[0])
        template = Template(DELETE_RESPONSE)
        return template.render(reservations=ec2_backend.all_reservations())

    def describe_tags(self):
        tags = ec2_backend.describe_tags()
        template = Template(DESCRIBE_RESPONSE)
        return template.render(tags=tags)


CREATE_RESPONSE = """<CreateTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</CreateTagsResponse>"""

DELETE_RESPONSE = """<DeleteTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
   <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
   <return>true</return>
</DeleteTagsResponse>"""

DESCRIBE_RESPONSE = """<DescribeTagsResponse xmlns="http://ec2.amazonaws.com/doc/2012-12-01/">
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
