from __future__ import unicode_literals
from datetime import datetime
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
        self.events = []
        self._add_stack_event("CREATE_IN_PROGRESS", resource_status_reason="User Initiated")

        self.description = self.template_dict.get('Description')
        self.resource_map = self._create_resource_map()
        self.output_map = self._create_output_map()
        self._add_stack_event("CREATE_COMPLETE")
        self.status = 'CREATE_COMPLETE'

    def _create_resource_map(self):
        resource_map = ResourceMap(self.stack_id, self.name, self.parameters, self.tags, self.region_name, self.template_dict)
        resource_map.create()
        return resource_map

    def _create_output_map(self):
        output_map = OutputMap(self.resource_map, self.template_dict)
        output_map.create()
        return output_map

    def _add_stack_event(self, resource_status, resource_status_reason=None, resource_properties=None):
        self.events.append(FakeEvent(
            stack_id=self.stack_id,
            stack_name=self.name,
            logical_resource_id=self.name,
            physical_resource_id=self.stack_id,
            resource_type="AWS::CloudFormation::Stack",
            resource_status=resource_status,
            resource_status_reason=resource_status_reason,
            resource_properties=resource_properties,
        ))

    def _add_resource_event(self, logical_resource_id, resource_status, resource_status_reason=None, resource_properties=None):
        # not used yet... feel free to help yourself
        resource = self.resource_map[logical_resource_id]
        self.events.append(FakeEvent(
            stack_id=self.stack_id,
            stack_name=self.name,
            logical_resource_id=logical_resource_id,
            physical_resource_id=resource.physical_resource_id,
            resource_type=resource.type,
            resource_status=resource_status,
            resource_status_reason=resource_status_reason,
            resource_properties=resource_properties,
        ))

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
        self._add_stack_event("UPDATE_IN_PROGRESS", resource_status_reason="User Initiated")
        self.template = template
        self.resource_map.update(json.loads(template))
        self.output_map = self._create_output_map()
        self._add_stack_event("UPDATE_COMPLETE")
        self.status = "UPDATE_COMPLETE"

    def delete(self):
        self._add_stack_event("DELETE_IN_PROGRESS", resource_status_reason="User Initiated")
        self.resource_map.delete()
        self._add_stack_event("DELETE_COMPLETE")
        self.status = "DELETE_COMPLETE"


class FakeEvent(object):
    def __init__(self, stack_id, stack_name, logical_resource_id, physical_resource_id, resource_type, resource_status, resource_status_reason=None, resource_properties=None):
        self.stack_id = stack_id
        self.stack_name = stack_name
        self.logical_resource_id = logical_resource_id
        self.physical_resource_id = physical_resource_id
        self.resource_type = resource_type
        self.resource_status = resource_status
        self.resource_status_reason = resource_status_reason
        self.resource_properties = resource_properties
        self.timestamp = datetime.utcnow()


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
        all_stacks = dict(self.deleted_stacks, **self.stacks)
        if name_or_stack_id in all_stacks:
            # Lookup by stack id - deleted stacks incldued
            return all_stacks[name_or_stack_id]
        else:
            # Lookup by stack name - undeleted stacks only
            for stack in self.stacks.values():
                if stack.name == name_or_stack_id:
                    return stack

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
