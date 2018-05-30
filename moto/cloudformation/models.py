from __future__ import unicode_literals
from datetime import datetime
import json
import yaml
import uuid

import boto.cloudformation
from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel

from .parsing import ResourceMap, OutputMap
from .utils import (
    generate_changeset_id,
    generate_stack_id,
    yaml_tag_constructor,
)
from .exceptions import ValidationError


class FakeStack(BaseModel):

    def __init__(self, stack_id, name, template, parameters, region_name, notification_arns=None, tags=None, role_arn=None, cross_stack_resources=None, create_change_set=False):
        self.stack_id = stack_id
        self.name = name
        self.template = template
        self._parse_template()
        self.parameters = parameters
        self.region_name = region_name
        self.notification_arns = notification_arns if notification_arns else []
        self.role_arn = role_arn
        self.tags = tags if tags else {}
        self.events = []
        if create_change_set:
            self._add_stack_event("REVIEW_IN_PROGRESS",
                                  resource_status_reason="User Initiated")
        else:
            self._add_stack_event("CREATE_IN_PROGRESS",
                                  resource_status_reason="User Initiated")

        self.description = self.template_dict.get('Description')
        self.cross_stack_resources = cross_stack_resources or {}
        self.resource_map = self._create_resource_map()
        self.output_map = self._create_output_map()
        self._add_stack_event("CREATE_COMPLETE")
        self.status = 'CREATE_COMPLETE'

    def _create_resource_map(self):
        resource_map = ResourceMap(
            self.stack_id, self.name, self.parameters, self.tags, self.region_name, self.template_dict, self.cross_stack_resources)
        resource_map.create()
        return resource_map

    def _create_output_map(self):
        output_map = OutputMap(self.resource_map, self.template_dict, self.stack_id)
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

    def _parse_template(self):
        yaml.add_multi_constructor('', yaml_tag_constructor)
        try:
            self.template_dict = yaml.load(self.template)
        except yaml.parser.ParserError:
            self.template_dict = json.loads(self.template)

    @property
    def stack_parameters(self):
        return self.resource_map.resolved_parameters

    @property
    def stack_resources(self):
        return self.resource_map.values()

    @property
    def stack_outputs(self):
        return self.output_map.values()

    @property
    def exports(self):
        return self.output_map.exports

    def update(self, template, role_arn=None, parameters=None, tags=None):
        self._add_stack_event("UPDATE_IN_PROGRESS", resource_status_reason="User Initiated")
        self.template = template
        self._parse_template()
        self.resource_map.update(self.template_dict, parameters)
        self.output_map = self._create_output_map()
        self._add_stack_event("UPDATE_COMPLETE")
        self.status = "UPDATE_COMPLETE"
        self.role_arn = role_arn
        # only overwrite tags if passed
        if tags is not None:
            self.tags = tags
            # TODO: update tags in the resource map

    def delete(self):
        self._add_stack_event("DELETE_IN_PROGRESS",
                              resource_status_reason="User Initiated")
        self.resource_map.delete()
        self._add_stack_event("DELETE_COMPLETE")
        self.status = "DELETE_COMPLETE"


class FakeEvent(BaseModel):

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
        self.event_id = uuid.uuid4()


class CloudFormationBackend(BaseBackend):

    def __init__(self):
        self.stacks = OrderedDict()
        self.deleted_stacks = {}
        self.exports = OrderedDict()
        self.change_sets = OrderedDict()

    def create_stack(self, name, template, parameters, region_name, notification_arns=None, tags=None, role_arn=None, create_change_set=False):
        stack_id = generate_stack_id(name)
        new_stack = FakeStack(
            stack_id=stack_id,
            name=name,
            template=template,
            parameters=parameters,
            region_name=region_name,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
            cross_stack_resources=self.exports,
            create_change_set=create_change_set,
        )
        self.stacks[stack_id] = new_stack
        self._validate_export_uniqueness(new_stack)
        for export in new_stack.exports:
            self.exports[export.name] = export
        return new_stack

    def create_change_set(self, stack_name, change_set_name, template, parameters, region_name, change_set_type, notification_arns=None, tags=None, role_arn=None):
        if change_set_type == 'UPDATE':
            stacks = self.stacks.values()
            stack = None
            for s in stacks:
                if s.name == stack_name:
                    stack = s
            if stack is None:
                raise ValidationError(stack_name)

        else:
            stack = self.create_stack(stack_name, template, parameters,
                                      region_name, notification_arns, tags,
                                      role_arn, create_change_set=True)
        change_set_id = generate_changeset_id(change_set_name, region_name)
        self.stacks[change_set_name] = {'Id': change_set_id,
                                        'StackId': stack.stack_id}
        self.change_sets[change_set_id] = stack
        return change_set_id, stack.stack_id

    def execute_change_set(self, change_set_name, stack_name=None):
        stack = None
        if change_set_name in self.change_sets:
            # This means arn was passed in
            stack = self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].name == change_set_name:
                    stack = self.change_sets[cs]
        if stack is None:
            raise ValidationError(stack_name)
        if stack.events[-1].resource_status == 'REVIEW_IN_PROGRESS':
            stack._add_stack_event('CREATE_COMPLETE')
        else:
            stack._add_stack_event('UPDATE_IN_PROGRESS')
            stack._add_stack_event('UPDATE_COMPLETE')
        return True

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
            return list(stacks)

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

    def update_stack(self, name, template, role_arn=None, parameters=None, tags=None):
        stack = self.get_stack(name)
        stack.update(template, role_arn, parameters=parameters, tags=tags)
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
            [self.exports.pop(export.name) for export in stack.exports]
            return self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            for stack in list(self.stacks.values()):
                if stack.name == name_or_stack_id:
                    self.delete_stack(stack.stack_id)

    def list_exports(self, token):
        all_exports = list(self.exports.values())
        if token is None:
            exports = all_exports[0:100]
            next_token = '100' if len(all_exports) > 100 else None
        else:
            token = int(token)
            exports = all_exports[token:token + 100]
            next_token = str(token + 100) if len(all_exports) > token + 100 else None
        return exports, next_token

    def _validate_export_uniqueness(self, stack):
        new_stack_export_names = [x.name for x in stack.exports]
        export_names = self.exports.keys()
        if not set(export_names).isdisjoint(new_stack_export_names):
            raise ValidationError(stack.stack_id, message='Export names must be unique across a given region')


cloudformation_backends = {}
for region in boto.cloudformation.regions():
    cloudformation_backends[region.name] = CloudFormationBackend()
