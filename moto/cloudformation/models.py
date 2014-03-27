import json

from moto.core import BaseBackend

from .parsing import ResourceMap
from .utils import generate_stack_id


class FakeStack(object):
    def __init__(self, stack_id, name, template):
        self.stack_id = stack_id
        self.name = name
        self.template = template

        template_dict = json.loads(self.template)
        self.description = template_dict.get('Description')

        self.resource_map = ResourceMap(stack_id, name, template_dict)
        self.resource_map.create()

    @property
    def stack_resources(self):
        return self.resource_map.values()


class CloudFormationBackend(BaseBackend):

    def __init__(self):
        self.stacks = {}

    def create_stack(self, name, template):
        stack_id = generate_stack_id(name)
        new_stack = FakeStack(stack_id=stack_id, name=name, template=template)
        self.stacks[stack_id] = new_stack
        return new_stack

    def describe_stacks(self, names):
        stacks = self.stacks.values()
        if names:
            return [stack for stack in stacks if stack.name in names]
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
            return self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            stack_to_delete = [stack for stack in self.stacks.values() if stack.name == name_or_stack_id][0]
            self.delete_stack(stack_to_delete.stack_id)


cloudformation_backend = CloudFormationBackend()
