from __future__ import unicode_literals
import json

import boto.cloudformation
from moto.core import BaseBackend

from .parsing import ResourceMap, OutputMap
from .utils import generate_stack_id
from .exceptions import ValidationError


class FakeStack(object):
    def __init__(self, stack_id, name, template, parameters, region_name, notification_arns=None, tags=None):
        self.stack_id = stack_id
        self.name = name
        self.template = template
        self.template_dict = json.loads(self.template)
        self.parameters = parameters
        self.region_name = region_name
        self.notification_arns = notification_arns if notification_arns else []
        self.tags = tags if tags else {}
        self.status = 'CREATE_COMPLETE'

        self.description = self.template_dict.get('Description')
        self.resource_map = self._create_resource_map()
        self.output_map = self._create_output_map()

    def _create_resource_map(self):
        resource_map = ResourceMap(self.stack_id, self.name, self.parameters, self.tags, self.region_name, self.template_dict)
        resource_map.create()
        return resource_map

    def _create_output_map(self):
        output_map = OutputMap(self.resource_map, self.template_dict)
        output_map.create()
        return output_map

    @property
    def stack_parameters(self):
        return self.resource_map.resolved_parameters

    @property
    def stack_resources(self):
        return self.resource_map.values()

    @property
    def stack_outputs(self):
        return self.output_map.values()

    def update(self, template):
        self.template = template
        self.resource_map.update(json.loads(template))
        self.output_map = self._create_output_map()
        self.status = "UPDATE_COMPLETE"

    def delete(self):
        self.resource_map.delete()
        self.status = "DELETE_COMPLETE"


class CloudFormationBackend(BaseBackend):

    def __init__(self):
        self.stacks = {}
        self.deleted_stacks = {}

    def create_stack(self, name, template, parameters, region_name, notification_arns=None, tags=None):
        stack_id = generate_stack_id(name)
        new_stack = FakeStack(
            stack_id=stack_id,
            name=name,
            template=template,
            parameters=parameters,
            region_name=region_name,
            notification_arns=notification_arns,
            tags=tags,
        )
        self.stacks[stack_id] = new_stack
        return new_stack

    def describe_stacks(self, name_or_stack_id):
        stacks = self.stacks.values()
        if name_or_stack_id:
            for stack in stacks:
                if stack.name == name_or_stack_id or stack.stack_id == name_or_stack_id:
                    return [stack]
            if self.deleted_stacks:
                deleted_stacks = self.deleted_stacks.values()
                for stack in deleted_stacks:
                    if stack.stack_id == name_or_stack_id:
                        return [stack]
            raise ValidationError(name_or_stack_id)
        else:
            return stacks

    def list_stacks(self):
        return self.stacks.values()

    def get_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Lookup by stack id
            return self.stacks.get(name_or_stack_id)
        else:
            # Lookup by stack name
            return [stack for stack in self.stacks.values() if stack.name == name_or_stack_id][0]

    def update_stack(self, name, template):
        stack = self.get_stack(name)
        stack.update(template)
        return stack

    def list_stack_resources(self, stack_name_or_id):
        stack = self.get_stack(stack_name_or_id)
        return stack.stack_resources

    def delete_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Delete by stack id
            stack = self.stacks.pop(name_or_stack_id, None)
            stack.delete()
            self.deleted_stacks[stack.stack_id] = stack
            return self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            for stack in list(self.stacks.values()):
                if stack.name == name_or_stack_id:
                    self.delete_stack(stack.stack_id)


cloudformation_backends = {}
for region in boto.cloudformation.regions():
    cloudformation_backends[region.name] = CloudFormationBackend()
