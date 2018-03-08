from __future__ import unicode_literals

import json
from six.moves.urllib.parse import urlparse

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from moto.s3 import s3_backend
from .models import cloudformation_backends
from .exceptions import ValidationError


class CloudFormationResponse(BaseResponse):

    @property
    def cloudformation_backend(self):
        return cloudformation_backends[self.region]

    def _get_stack_from_s3_url(self, template_url):
        template_url_parts = urlparse(template_url)
        if "localhost" in template_url:
            bucket_name, key_name = template_url_parts.path.lstrip(
                "/").split("/", 1)
        else:
            if template_url_parts.netloc.endswith('amazonaws.com') \
                    and template_url_parts.netloc.startswith('s3'):
                # Handle when S3 url uses amazon url with bucket in path
                # Also handles getting region as technically s3 is region'd

                # region = template_url.netloc.split('.')[1]
                bucket_name, key_name = template_url_parts.path.lstrip(
                    "/").split("/", 1)
            else:
                bucket_name = template_url_parts.netloc.split(".")[0]
                key_name = template_url_parts.path.lstrip("/")

        key = s3_backend.get_key(bucket_name, key_name)
        return key.value.decode("utf-8")

    def create_stack(self):
        stack_name = self._get_param('StackName')
        stack_body = self._get_param('TemplateBody')
        template_url = self._get_param('TemplateURL')
        role_arn = self._get_param('RoleARN')
        parameters_list = self._get_list_prefix("Parameters.member")
        tags = dict((item['key'], item['value'])
                    for item in self._get_list_prefix("Tags.member"))

        # Hack dict-comprehension
        parameters = dict([
            (parameter['parameter_key'], parameter['parameter_value'])
            for parameter
            in parameters_list
        ])
        if template_url:
            stack_body = self._get_stack_from_s3_url(template_url)
        stack_notification_arns = self._get_multi_param(
            'NotificationARNs.member')

        stack = self.cloudformation_backend.create_stack(
            name=stack_name,
            template=stack_body,
            parameters=parameters,
            region_name=self.region,
            notification_arns=stack_notification_arns,
            tags=tags,
            role_arn=role_arn,
        )
        if self.request_json:
            return json.dumps({
                'CreateStackResponse': {
                    'CreateStackResult': {
                        'StackId': stack.stack_id,
                    }
                }
            })
        else:
            template = self.response_template(CREATE_STACK_RESPONSE_TEMPLATE)
            return template.render(stack=stack)

    @amzn_request_id
    def create_change_set(self):
        stack_name = self._get_param('StackName')
        change_set_name = self._get_param('ChangeSetName')
        stack_body = self._get_param('TemplateBody')
        template_url = self._get_param('TemplateURL')
        role_arn = self._get_param('RoleARN')
        update_or_create = self._get_param('ChangeSetType', 'CREATE')
        parameters_list = self._get_list_prefix("Parameters.member")
        tags = {tag[0]: tag[1] for tag in self._get_list_prefix("Tags.member")}
        parameters = {param['parameter_key']: param['parameter_value']
                      for param in parameters_list}
        if template_url:
            stack_body = self._get_stack_from_s3_url(template_url)
        stack_notification_arns = self._get_multi_param(
            'NotificationARNs.member')
        change_set_id, stack_id = self.cloudformation_backend.create_change_set(
            stack_name=stack_name,
            change_set_name=change_set_name,
            template=stack_body,
            parameters=parameters,
            region_name=self.region,
            notification_arns=stack_notification_arns,
            tags=tags,
            role_arn=role_arn,
            change_set_type=update_or_create,
        )
        if self.request_json:
            return json.dumps({
                'CreateChangeSetResponse': {
                    'CreateChangeSetResult': {
                        'Id': change_set_id,
                        'StackId': stack_id,
                    }
                }
            })
        else:
            template = self.response_template(CREATE_CHANGE_SET_RESPONSE_TEMPLATE)
            return template.render(stack_id=stack_id, change_set_id=change_set_id)

    @amzn_request_id
    def execute_change_set(self):
        stack_name = self._get_param('StackName')
        change_set_name = self._get_param('ChangeSetName')
        self.cloudformation_backend.execute_change_set(
            stack_name=stack_name,
            change_set_name=change_set_name,
        )
        if self.request_json:
            return json.dumps({
                'ExecuteChangeSetResponse': {
                    'ExecuteChangeSetResult': {},
                }
            })
        else:
            template = self.response_template(EXECUTE_CHANGE_SET_RESPONSE_TEMPLATE)
            return template.render()

    def describe_stacks(self):
        stack_name_or_id = None
        if self._get_param('StackName'):
            stack_name_or_id = self.querystring.get('StackName')[0]
        token = self._get_param('NextToken')
        stacks = self.cloudformation_backend.describe_stacks(stack_name_or_id)
        stack_ids = [stack.stack_id for stack in stacks]
        if token:
            start = stack_ids.index(token) + 1
        else:
            start = 0
        max_results = 50  # using this to mske testing of paginated stacks more convenient than default 1 MB
        stacks_resp = stacks[start:start + max_results]
        next_token = None
        if len(stacks) > (start + max_results):
            next_token = stacks_resp[-1].stack_id
        template = self.response_template(DESCRIBE_STACKS_TEMPLATE)
        return template.render(stacks=stacks_resp, next_token=next_token)

    def describe_stack_resource(self):
        stack_name = self._get_param('StackName')
        stack = self.cloudformation_backend.get_stack(stack_name)
        logical_resource_id = self._get_param('LogicalResourceId')

        for stack_resource in stack.stack_resources:
            if stack_resource.logical_resource_id == logical_resource_id:
                resource = stack_resource
                break
        else:
            raise ValidationError(logical_resource_id)

        template = self.response_template(
            DESCRIBE_STACK_RESOURCE_RESPONSE_TEMPLATE)
        return template.render(stack=stack, resource=resource)

    def describe_stack_resources(self):
        stack_name = self._get_param('StackName')
        stack = self.cloudformation_backend.get_stack(stack_name)

        template = self.response_template(DESCRIBE_STACK_RESOURCES_RESPONSE)
        return template.render(stack=stack)

    def describe_stack_events(self):
        stack_name = self._get_param('StackName')
        stack = self.cloudformation_backend.get_stack(stack_name)

        template = self.response_template(DESCRIBE_STACK_EVENTS_RESPONSE)
        return template.render(stack=stack)

    def list_stacks(self):
        stacks = self.cloudformation_backend.list_stacks()
        template = self.response_template(LIST_STACKS_RESPONSE)
        return template.render(stacks=stacks)

    def list_stack_resources(self):
        stack_name_or_id = self._get_param('StackName')
        resources = self.cloudformation_backend.list_stack_resources(
            stack_name_or_id)

        template = self.response_template(LIST_STACKS_RESOURCES_RESPONSE)
        return template.render(resources=resources)

    def get_template(self):
        name_or_stack_id = self.querystring.get('StackName')[0]
        stack = self.cloudformation_backend.get_stack(name_or_stack_id)

        if self.request_json:
            return json.dumps({
                "GetTemplateResponse": {
                    "GetTemplateResult": {
                        "TemplateBody": stack.template,
                        "ResponseMetadata": {
                            "RequestId": "2d06e36c-ac1d-11e0-a958-f9382b6eb86bEXAMPLE"
                        }
                    }
                }
            })
        else:
            template = self.response_template(GET_TEMPLATE_RESPONSE_TEMPLATE)
            return template.render(stack=stack)

    def update_stack(self):
        stack_name = self._get_param('StackName')
        role_arn = self._get_param('RoleARN')
        template_url = self._get_param('TemplateURL')
        stack_body = self._get_param('TemplateBody')
        stack = self.cloudformation_backend.get_stack(stack_name)
        if self._get_param('UsePreviousTemplate') == "true":
            stack_body = stack.template
        elif not stack_body and template_url:
            stack_body = self._get_stack_from_s3_url(template_url)

        incoming_params = self._get_list_prefix("Parameters.member")
        parameters = dict([
            (parameter['parameter_key'], parameter['parameter_value'])
            for parameter
            in incoming_params if 'parameter_value' in parameter
        ])
        previous = dict([
            (parameter['parameter_key'], stack.parameters[parameter['parameter_key']])
            for parameter
            in incoming_params if 'use_previous_value' in parameter
        ])
        parameters.update(previous)
        # boto3 is supposed to let you clear the tags by passing an empty value, but the request body doesn't
        # end up containing anything we can use to differentiate between passing an empty value versus not
        # passing anything. so until that changes, moto won't be able to clear tags, only update them.
        tags = dict((item['key'], item['value'])
                    for item in self._get_list_prefix("Tags.member"))
        # so that if we don't pass the parameter, we don't clear all the tags accidentally
        if not tags:
            tags = None

        stack = self.cloudformation_backend.get_stack(stack_name)
        if stack.status == 'ROLLBACK_COMPLETE':
            raise ValidationError(
                stack.stack_id, message="Stack:{0} is in ROLLBACK_COMPLETE state and can not be updated.".format(stack.stack_id))

        stack = self.cloudformation_backend.update_stack(
            name=stack_name,
            template=stack_body,
            role_arn=role_arn,
            parameters=parameters,
            tags=tags,
        )
        if self.request_json:
            stack_body = {
                'UpdateStackResponse': {
                    'UpdateStackResult': {
                        'StackId': stack.name,
                    }
                }
            }
            return json.dumps(stack_body)
        else:
            template = self.response_template(UPDATE_STACK_RESPONSE_TEMPLATE)
            return template.render(stack=stack)

    def delete_stack(self):
        name_or_stack_id = self.querystring.get('StackName')[0]

        self.cloudformation_backend.delete_stack(name_or_stack_id)
        if self.request_json:
            return json.dumps({
                'DeleteStackResponse': {
                    'DeleteStackResult': {},
                }
            })
        else:
            template = self.response_template(DELETE_STACK_RESPONSE_TEMPLATE)
            return template.render()

    def list_exports(self):
        token = self._get_param('NextToken')
        exports, next_token = self.cloudformation_backend.list_exports(token=token)
        template = self.response_template(LIST_EXPORTS_RESPONSE)
        return template.render(exports=exports, next_token=next_token)


CREATE_STACK_RESPONSE_TEMPLATE = """<CreateStackResponse>
  <CreateStackResult>
    <StackId>{{ stack.stack_id }}</StackId>
  </CreateStackResult>
  <ResponseMetadata>
    <RequestId>b9b4b068-3a41-11e5-94eb-example</RequestId>
    </ResponseMetadata>
</CreateStackResponse>
"""

UPDATE_STACK_RESPONSE_TEMPLATE = """<UpdateStackResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <UpdateStackResult>
    <StackId>{{ stack.stack_id }}</StackId>
  </UpdateStackResult>
  <ResponseMetadata>
    <RequestId>b9b4b068-3a41-11e5-94eb-example</RequestId>
  </ResponseMetadata>
</UpdateStackResponse>
"""

CREATE_CHANGE_SET_RESPONSE_TEMPLATE = """<CreateStackResponse>
  <CreateChangeSetResult>
    <Id>{{change_set_id}}</Id>
    <StackId>{{ stack_id }}</StackId>
  </CreateChangeSetResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</CreateStackResponse>
"""

EXECUTE_CHANGE_SET_RESPONSE_TEMPLATE = """<ExecuteChangeSetResponse>
  <ExecuteChangeSetResult>
      <ExecuteChangeSetResult/>
  </ExecuteChangeSetResult>
  <ResponseMetadata>
    <RequestId>{{ request_id }}</RequestId>
  </ResponseMetadata>
</ExecuteChangeSetResponse>
"""

DESCRIBE_STACKS_TEMPLATE = """<DescribeStacksResponse>
  <DescribeStacksResult>
    <Stacks>
      {% for stack in stacks %}
      <member>
        <StackName>{{ stack.name }}</StackName>
        <StackId>{{ stack.stack_id }}</StackId>
        <CreationTime>2010-07-27T22:28:28Z</CreationTime>
        <StackStatus>{{ stack.status }}</StackStatus>
        {% if stack.notification_arns %}
        <NotificationARNs>
          {% for notification_arn in stack.notification_arns %}
          <member>{{ notification_arn }}</member>
          {% endfor %}
        </NotificationARNs>
        {% else %}
        <NotificationARNs/>
        {% endif %}
        <DisableRollback>false</DisableRollback>
        <Outputs>
        {% for output in stack.stack_outputs %}
          <member>
            <OutputKey>{{ output.key }}</OutputKey>
            <OutputValue>{{ output.value }}</OutputValue>
          </member>
        {% endfor %}
        </Outputs>
        <Parameters>
        {% for param_name, param_value in stack.stack_parameters.items() %}
          <member>
            <ParameterKey>{{ param_name }}</ParameterKey>
            <ParameterValue>{{ param_value }}</ParameterValue>
          </member>
        {% endfor %}
        </Parameters>
        {% if stack.role_arn %}
        <RoleARN>{{ stack.role_arn }}</RoleARN>
        {% endif %}
        <Tags>
          {% for tag_key, tag_value in stack.tags.items() %}
            <member>
              <Key>{{ tag_key }}</Key>
              <Value>{{ tag_value }}</Value>
            </member>
          {% endfor %}
        </Tags>
      </member>
      {% endfor %}
    </Stacks>
    {% if next_token %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </DescribeStacksResult>
</DescribeStacksResponse>"""


DESCRIBE_STACK_RESOURCE_RESPONSE_TEMPLATE = """<DescribeStackResourceResponse>
  <DescribeStackResourceResult>
    <StackResourceDetail>
      <StackId>{{ stack.stack_id }}</StackId>
      <StackName>{{ stack.name }}</StackName>
      <LogicalResourceId>{{ resource.logical_resource_id }}</LogicalResourceId>
      <PhysicalResourceId>{{ resource.physical_resource_id }}</PhysicalResourceId>
      <ResourceType>{{ resource.type }}</ResourceType>
      <Timestamp>2010-07-27T22:27:28Z</Timestamp>
      <ResourceStatus>{{ stack.status }}</ResourceStatus>
    </StackResourceDetail>
  </DescribeStackResourceResult>
</DescribeStackResourceResponse>"""


DESCRIBE_STACK_RESOURCES_RESPONSE = """<DescribeStackResourcesResponse>
    <DescribeStackResourcesResult>
      <StackResources>
        {% for resource in stack.stack_resources %}
        <member>
          <StackId>{{ stack.stack_id }}</StackId>
          <StackName>{{ stack.name }}</StackName>
          <LogicalResourceId>{{ resource.logical_resource_id }}</LogicalResourceId>
          <PhysicalResourceId>{{ resource.physical_resource_id }}</PhysicalResourceId>
          <ResourceType>{{ resource.type }}</ResourceType>
          <Timestamp>2010-07-27T22:27:28Z</Timestamp>
          <ResourceStatus>{{ stack.status }}</ResourceStatus>
        </member>
        {% endfor %}
      </StackResources>
    </DescribeStackResourcesResult>
</DescribeStackResourcesResponse>"""


DESCRIBE_STACK_EVENTS_RESPONSE = """<DescribeStackEventsResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <DescribeStackEventsResult>
    <StackEvents>
      {% for event in stack.events[::-1] %}
      <member>
        <Timestamp>{{ event.timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ') }}</Timestamp>
        <ResourceStatus>{{ event.resource_status }}</ResourceStatus>
        <StackId>{{ event.stack_id }}</StackId>
        <EventId>{{ event.event_id }}</EventId>
        <LogicalResourceId>{{ event.logical_resource_id }}</LogicalResourceId>
        {% if event.resource_status_reason %}<ResourceStatusReason>{{ event.resource_status_reason }}</ResourceStatusReason>{% endif %}
        <StackName>{{ event.stack_name }}</StackName>
        <PhysicalResourceId>{{ event.physical_resource_id }}</PhysicalResourceId>
        {% if event.resource_properties %}<ResourceProperties>{{ event.resource_properties }}</ResourceProperties>{% endif %}
        <ResourceType>{{ event.resource_type }}</ResourceType>
      </member>
      {% endfor %}
    </StackEvents>
  </DescribeStackEventsResult>
  <ResponseMetadata>
    <RequestId>b9b4b068-3a41-11e5-94eb-example</RequestId>
  </ResponseMetadata>
</DescribeStackEventsResponse>"""


LIST_STACKS_RESPONSE = """<ListStacksResponse>
 <ListStacksResult>
  <StackSummaries>
    {% for stack in stacks %}
    <member>
        <StackId>{{ stack.stack_id }}</StackId>
        <StackStatus>{{ stack.status }}</StackStatus>
        <StackName>{{ stack.name }}</StackName>
        <CreationTime>2011-05-23T15:47:44Z</CreationTime>
        <TemplateDescription>{{ stack.description }}</TemplateDescription>
    </member>
    {% endfor %}
  </StackSummaries>
 </ListStacksResult>
</ListStacksResponse>"""


LIST_STACKS_RESOURCES_RESPONSE = """<ListStackResourcesResponse>
  <ListStackResourcesResult>
    <StackResourceSummaries>
      {% for resource in resources %}
      <member>
        <ResourceStatus>CREATE_COMPLETE</ResourceStatus>
        <LogicalResourceId>{{ resource.logical_resource_id }}</LogicalResourceId>
        <LastUpdatedTimestamp>2011-06-21T20:15:58Z</LastUpdatedTimestamp>
        <PhysicalResourceId>{{ resource.physical_resource_id }}</PhysicalResourceId>
        <ResourceType>{{ resource.type }}</ResourceType>
      </member>
      {% endfor %}
    </StackResourceSummaries>
  </ListStackResourcesResult>
  <ResponseMetadata>
    <RequestId>2d06e36c-ac1d-11e0-a958-f9382b6eb86b</RequestId>
  </ResponseMetadata>
</ListStackResourcesResponse>"""


GET_TEMPLATE_RESPONSE_TEMPLATE = """<GetTemplateResponse>
  <GetTemplateResult>
    <TemplateBody>{{ stack.template }}</TemplateBody>
  </GetTemplateResult>
  <ResponseMetadata>
    <RequestId>b9b4b068-3a41-11e5-94eb-example</RequestId>
  </ResponseMetadata>
</GetTemplateResponse>"""


DELETE_STACK_RESPONSE_TEMPLATE = """<DeleteStackResponse>
  <ResponseMetadata>
    <RequestId>5ccc7dcd-744c-11e5-be70-example</RequestId>
  </ResponseMetadata>
</DeleteStackResponse>
"""


LIST_EXPORTS_RESPONSE = """<ListExportsResponse xmlns="http://cloudformation.amazonaws.com/doc/2010-05-15/">
  <ListExportsResult>
    <Exports>
      {% for export in exports %}
      <member>
        <ExportingStackId>{{ export.exporting_stack_id }}</ExportingStackId>
        <Name>{{ export.name }}</Name>
        <Value>{{ export.value }}</Value>
      </member>
      {% endfor %}
    </Exports>
    {% if next_token %}
    <NextToken>{{ next_token }}</NextToken>
    {% endif %}
  </ListExportsResult>
  <ResponseMetadata>
    <RequestId>5ccc7dcd-744c-11e5-be70-example</RequestId>
  </ResponseMetadata>
</ListExportsResponse>"""
