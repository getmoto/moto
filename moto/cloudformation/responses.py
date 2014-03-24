import json

from jinja2 import Template

from moto.core.responses import BaseResponse
from .models import cloudformation_backend


class CloudFormationResponse(BaseResponse):

    def create_stack(self):
        stack_name = self._get_param('StackName')
        stack_body = self._get_param('TemplateBody')

        stack = cloudformation_backend.create_stack(
            name=stack_name,
            template=stack_body,
        )
        stack_body = {
            'CreateStackResponse': {
                'CreateStackResult': {
                    'StackId': stack.name,
                }
            }
        }
        return json.dumps(stack_body)

    def describe_stacks(self):
        names = [value[0] for key, value in self.querystring.items() if "StackName" in key]
        stacks = cloudformation_backend.describe_stacks(names)

        template = Template(DESCRIBE_STACKS_TEMPLATE)
        return template.render(stacks=stacks)

    def describe_stack_resources(self):
        stack_name = self._get_param('StackName')
        stack = cloudformation_backend.get_stack(stack_name)

        template = Template(LIST_STACKS_RESOURCES_RESPONSE)
        return template.render(stack=stack)

    def list_stacks(self):
        stacks = cloudformation_backend.list_stacks()
        template = Template(LIST_STACKS_RESPONSE)
        return template.render(stacks=stacks)

    def get_template(self):
        name_or_stack_id = self.querystring.get('StackName')[0]

        stack = cloudformation_backend.get_stack(name_or_stack_id)
        return stack.template

    # def update_stack(self):
    #     stack_name = self._get_param('StackName')
    #     stack_body = self._get_param('TemplateBody')

    #     stack = cloudformation_backend.update_stack(
    #         name=stack_name,
    #         template=stack_body,
    #     )
    #     stack_body = {
    #         'UpdateStackResponse': {
    #             'UpdateStackResult': {
    #                 'StackId': stack.name,
    #             }
    #         }
    #     }
    #     return json.dumps(stack_body)

    def delete_stack(self):
        name_or_stack_id = self.querystring.get('StackName')[0]

        cloudformation_backend.delete_stack(name_or_stack_id)
        return json.dumps({
            'DeleteStackResponse': {
                'DeleteStackResult': {},
            }
        })


DESCRIBE_STACKS_TEMPLATE = """<DescribeStacksResult>
  <Stacks>
    {% for stack in stacks %}
    <member>
      <StackName>{{ stack.name }}</StackName>
      <StackId>{{ stack.stack_id }}</StackId>
      <CreationTime>2010-07-27T22:28:28Z</CreationTime>
      <StackStatus>CREATE_COMPLETE</StackStatus>
      <DisableRollback>false</DisableRollback>
      <Outputs></Outputs>
    </member>
    {% endfor %}
  </Stacks>
</DescribeStacksResult>"""


LIST_STACKS_RESPONSE = """<ListStacksResponse>
 <ListStacksResult>
  <StackSummaries>
    {% for stack in stacks %}
    <member>
        <StackId>{{ stack.id }}</StackId>
        <StackStatus>CREATE_IN_PROGRESS</StackStatus>
        <StackName>{{ stack.name }}</StackName>
        <CreationTime>2011-05-23T15:47:44Z</CreationTime>
        <TemplateDescription>{{ stack.description }}</TemplateDescription>
    </member>
    {% endfor %}
  </StackSummaries>
 </ListStacksResult>
</ListStacksResponse>"""


LIST_STACKS_RESOURCES_RESPONSE = """<DescribeStackResourcesResult>
  <StackResources>
    {% for resource in stack.stack_resources %}
    <member>
      <StackId>{{ stack.stack_id }}</StackId>
      <StackName>{{ stack.name }}</StackName>
      <LogicalResourceId>{{ resource.logical_resource_id }}</LogicalResourceId>
      <PhysicalResourceId>{{ resource.physical_resource_id }}</PhysicalResourceId>
      <ResourceType>{{ resource.type }}</ResourceType>
      <Timestamp>2010-07-27T22:27:28Z</Timestamp>
      <ResourceStatus>CREATE_COMPLETE</ResourceStatus>
    </member>
    {% endfor %}
  </StackResources>
</DescribeStackResourcesResult>"""
