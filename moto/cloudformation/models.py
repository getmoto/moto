from __future__ import unicode_literals
import json

from moto.core import BaseBackend

from .parsing import ResourceMap, OutputMap
from .utils import generate_stack_id
from .exceptions import ValidationError


class FakeStack(object):
    def __init__(self, stack_id, name, template, notification_arns=None):
        self.stack_id = stack_id
        self.name = name
        self.notification_arns = notification_arns if notification_arns else []
        self.template = template
        self.status = 'CREATE_COMPLETE'

        template_dict = json.loads(self.template)
        self.description = template_dict.get('Description')

        self.resource_map = ResourceMap(stack_id, name, template_dict)
        self.resource_map.create()

        self.output_map = OutputMap(self.resource_map, template_dict)
        self.output_map.create()

    @property
    def stack_resources(self):
        return self.resource_map.values()

    @property
    def stack_outputs(self):
        return self.output_map.values()


class CloudFormationBackend(BaseBackend):

    def __init__(self):
        self.stacks = {}
        self.deleted_stacks = {}

    def create_stack(self, name, template, notification_arns=None):
        stack_id = generate_stack_id(name)
        new_stack = FakeStack(stack_id=stack_id, name=name, template=template, notification_arns=notification_arns)
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

    # def update_stack(self, name, template):
    #     stack = self.get_stack(name)
    #     stack.template = template
    #     return stack

    def delete_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Delete by stack id
            stack = self.stacks.pop(name_or_stack_id, None)
            stack.status = 'DELETE_COMPLETE'
            self.deleted_stacks[stack.stack_id] = stack
            return self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            stack_to_delete = [stack for stack in self.stacks.values() if stack.name == name_or_stack_id][0]
            self.delete_stack(stack_to_delete.stack_id)


cloudformation_backend = CloudFormationBackend()
