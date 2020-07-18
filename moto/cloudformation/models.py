from __future__ import unicode_literals
from datetime import datetime, timedelta
import json
import yaml
import uuid

from boto3 import Session

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_without_milliseconds

from .parsing import ResourceMap, OutputMap
from .utils import (
    generate_changeset_id,
    generate_stack_id,
    generate_stackset_arn,
    generate_stackset_id,
    yaml_tag_constructor,
    validate_template_cfn_lint,
)
from .exceptions import ValidationError


class FakeStackSet(BaseModel):
    def __init__(
        self,
        stackset_id,
        name,
        template,
        region="us-east-1",
        status="ACTIVE",
        description=None,
        parameters=None,
        tags=None,
        admin_role="AWSCloudFormationStackSetAdministrationRole",
        execution_role="AWSCloudFormationStackSetExecutionRole",
    ):
        self.id = stackset_id
        self.arn = generate_stackset_arn(stackset_id, region)
        self.name = name
        self.template = template
        self.description = description
        self.parameters = parameters
        self.tags = tags
        self.admin_role = admin_role
        self.execution_role = execution_role
        self.status = status
        self.instances = FakeStackInstances(parameters, self.id, self.name)
        self.stack_instances = self.instances.stack_instances
        self.operations = []

    def _create_operation(self, operation_id, action, status, accounts=[], regions=[]):
        operation = {
            "OperationId": str(operation_id),
            "Action": action,
            "Status": status,
            "CreationTimestamp": datetime.now(),
            "EndTimestamp": datetime.now() + timedelta(minutes=2),
            "Instances": [
                {account: region} for account in accounts for region in regions
            ],
        }

        self.operations += [operation]
        return operation

    def get_operation(self, operation_id):
        for operation in self.operations:
            if operation_id == operation["OperationId"]:
                return operation
        raise ValidationError(operation_id)

    def update_operation(self, operation_id, status):
        operation = self.get_operation(operation_id)
        operation["Status"] = status
        return operation_id

    def delete(self):
        self.status = "DELETED"

    def update(
        self,
        template,
        description,
        parameters,
        tags,
        admin_role,
        execution_role,
        accounts,
        regions,
        operation_id=None,
    ):
        if not operation_id:
            operation_id = uuid.uuid4()

        self.template = template if template else self.template
        self.description = description if description is not None else self.description
        self.parameters = parameters if parameters else self.parameters
        self.tags = tags if tags else self.tags
        self.admin_role = admin_role if admin_role else self.admin_role
        self.execution_role = execution_role if execution_role else self.execution_role

        if accounts and regions:
            self.update_instances(accounts, regions, self.parameters)

        operation = self._create_operation(
            operation_id=operation_id,
            action="UPDATE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )
        return operation

    def create_stack_instances(self, accounts, regions, parameters, operation_id=None):
        if not operation_id:
            operation_id = uuid.uuid4()
        if not parameters:
            parameters = self.parameters

        self.instances.create_instances(accounts, regions, parameters, operation_id)
        self._create_operation(
            operation_id=operation_id,
            action="CREATE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )

    def delete_stack_instances(self, accounts, regions, operation_id=None):
        if not operation_id:
            operation_id = uuid.uuid4()

        self.instances.delete(accounts, regions)

        operation = self._create_operation(
            operation_id=operation_id,
            action="DELETE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )
        return operation

    def update_instances(self, accounts, regions, parameters, operation_id=None):
        if not operation_id:
            operation_id = uuid.uuid4()

        self.instances.update(accounts, regions, parameters)
        operation = self._create_operation(
            operation_id=operation_id,
            action="UPDATE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )
        return operation


class FakeStackInstances(BaseModel):
    def __init__(self, parameters, stackset_id, stackset_name):
        self.parameters = parameters if parameters else {}
        self.stackset_id = stackset_id
        self.stack_name = "StackSet-{}".format(stackset_id)
        self.stackset_name = stackset_name
        self.stack_instances = []

    def create_instances(self, accounts, regions, parameters, operation_id):
        new_instances = []
        for region in regions:
            for account in accounts:
                instance = {
                    "StackId": generate_stack_id(self.stack_name, region, account),
                    "StackSetId": self.stackset_id,
                    "Region": region,
                    "Account": account,
                    "Status": "CURRENT",
                    "ParameterOverrides": parameters if parameters else [],
                }
                new_instances.append(instance)
        self.stack_instances += new_instances
        return new_instances

    def update(self, accounts, regions, parameters):
        for account in accounts:
            for region in regions:
                instance = self.get_instance(account, region)
                if parameters:
                    instance["ParameterOverrides"] = parameters
                else:
                    instance["ParameterOverrides"] = []

    def delete(self, accounts, regions):
        for i, instance in enumerate(self.stack_instances):
            if instance["Region"] in regions and instance["Account"] in accounts:
                self.stack_instances.pop(i)

    def get_instance(self, account, region):
        for i, instance in enumerate(self.stack_instances):
            if instance["Region"] == region and instance["Account"] == account:
                return self.stack_instances[i]


class FakeStack(BaseModel):
    def __init__(
        self,
        stack_id,
        name,
        template,
        parameters,
        region_name,
        notification_arns=None,
        tags=None,
        role_arn=None,
        cross_stack_resources=None,
        create_change_set=False,
    ):
        self.stack_id = stack_id
        self.name = name
        self.template = template
        if template != {}:
            self._parse_template()
            self.description = self.template_dict.get("Description")
        else:
            self.template_dict = {}
            self.description = None
        self.parameters = parameters
        self.region_name = region_name
        self.notification_arns = notification_arns if notification_arns else []
        self.role_arn = role_arn
        self.tags = tags if tags else {}
        self.events = []
        if create_change_set:
            self._add_stack_event(
                "REVIEW_IN_PROGRESS", resource_status_reason="User Initiated"
            )
        else:
            self._add_stack_event(
                "CREATE_IN_PROGRESS", resource_status_reason="User Initiated"
            )

        self.cross_stack_resources = cross_stack_resources or {}
        self.resource_map = self._create_resource_map()
        self.output_map = self._create_output_map()
        if create_change_set:
            self.status = "CREATE_COMPLETE"
            self.execution_status = "AVAILABLE"
        else:
            self.create_resources()
            self._add_stack_event("CREATE_COMPLETE")
        self.creation_time = datetime.utcnow()

    def _create_resource_map(self):
        resource_map = ResourceMap(
            self.stack_id,
            self.name,
            self.parameters,
            self.tags,
            self.region_name,
            self.template_dict,
            self.cross_stack_resources,
        )
        resource_map.load()
        return resource_map

    def _create_output_map(self):
        output_map = OutputMap(self.resource_map, self.template_dict, self.stack_id)
        output_map.create()
        return output_map

    @property
    def creation_time_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.creation_time)

    def _add_stack_event(
        self, resource_status, resource_status_reason=None, resource_properties=None
    ):
        self.events.append(
            FakeEvent(
                stack_id=self.stack_id,
                stack_name=self.name,
                logical_resource_id=self.name,
                physical_resource_id=self.stack_id,
                resource_type="AWS::CloudFormation::Stack",
                resource_status=resource_status,
                resource_status_reason=resource_status_reason,
                resource_properties=resource_properties,
            )
        )

    def _add_resource_event(
        self,
        logical_resource_id,
        resource_status,
        resource_status_reason=None,
        resource_properties=None,
    ):
        # not used yet... feel free to help yourself
        resource = self.resource_map[logical_resource_id]
        self.events.append(
            FakeEvent(
                stack_id=self.stack_id,
                stack_name=self.name,
                logical_resource_id=logical_resource_id,
                physical_resource_id=resource.physical_resource_id,
                resource_type=resource.type,
                resource_status=resource_status,
                resource_status_reason=resource_status_reason,
                resource_properties=resource_properties,
            )
        )

    def _parse_template(self):
        yaml.add_multi_constructor("", yaml_tag_constructor)
        try:
            self.template_dict = yaml.load(self.template, Loader=yaml.Loader)
        except (yaml.parser.ParserError, yaml.scanner.ScannerError):
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

    def create_resources(self):
        self.resource_map.create(self.template_dict)
        # Set the description of the stack
        self.description = self.template_dict.get("Description")
        self.status = "CREATE_COMPLETE"

    def update(self, template, role_arn=None, parameters=None, tags=None):
        self._add_stack_event(
            "UPDATE_IN_PROGRESS", resource_status_reason="User Initiated"
        )
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
        self._add_stack_event(
            "DELETE_IN_PROGRESS", resource_status_reason="User Initiated"
        )
        self.resource_map.delete()
        self._add_stack_event("DELETE_COMPLETE")
        self.status = "DELETE_COMPLETE"


class FakeChange(BaseModel):
    def __init__(self, action, logical_resource_id, resource_type):
        self.action = action
        self.logical_resource_id = logical_resource_id
        self.resource_type = resource_type


class FakeChangeSet(FakeStack):
    def __init__(
        self,
        stack_id,
        stack_name,
        stack_template,
        change_set_id,
        change_set_name,
        template,
        parameters,
        region_name,
        notification_arns=None,
        tags=None,
        role_arn=None,
        cross_stack_resources=None,
    ):
        super(FakeChangeSet, self).__init__(
            stack_id,
            stack_name,
            stack_template,
            parameters,
            region_name,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
            cross_stack_resources=cross_stack_resources,
            create_change_set=True,
        )
        self.stack_name = stack_name
        self.change_set_id = change_set_id
        self.change_set_name = change_set_name
        self.changes = self.diff(template=template, parameters=parameters)
        if self.description is None:
            self.description = self.template_dict.get("Description")
        self.creation_time = datetime.utcnow()

    def diff(self, template, parameters=None):
        self.template = template
        self._parse_template()
        changes = []
        resources_by_action = self.resource_map.diff(self.template_dict, parameters)
        for action, resources in resources_by_action.items():
            for resource_name, resource in resources.items():
                changes.append(
                    FakeChange(
                        action=action,
                        logical_resource_id=resource_name,
                        resource_type=resource["ResourceType"],
                    )
                )
        return changes


class FakeEvent(BaseModel):
    def __init__(
        self,
        stack_id,
        stack_name,
        logical_resource_id,
        physical_resource_id,
        resource_type,
        resource_status,
        resource_status_reason=None,
        resource_properties=None,
    ):
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


def filter_stacks(all_stacks, status_filter):
    filtered_stacks = []
    if not status_filter:
        return all_stacks
    for stack in all_stacks:
        if stack.status in status_filter:
            filtered_stacks.append(stack)
    return filtered_stacks


class CloudFormationBackend(BaseBackend):
    def __init__(self):
        self.stacks = OrderedDict()
        self.stacksets = OrderedDict()
        self.deleted_stacks = {}
        self.exports = OrderedDict()
        self.change_sets = OrderedDict()

    def create_stack_set(
        self,
        name,
        template,
        parameters,
        tags=None,
        description=None,
        region="us-east-1",
        admin_role=None,
        execution_role=None,
    ):
        stackset_id = generate_stackset_id(name)
        new_stackset = FakeStackSet(
            stackset_id=stackset_id,
            name=name,
            template=template,
            parameters=parameters,
            description=description,
            tags=tags,
            admin_role=admin_role,
            execution_role=execution_role,
        )
        self.stacksets[stackset_id] = new_stackset
        return new_stackset

    def get_stack_set(self, name):
        stacksets = self.stacksets.keys()
        for stackset in stacksets:
            if self.stacksets[stackset].name == name:
                return self.stacksets[stackset]
        raise ValidationError(name)

    def delete_stack_set(self, name):
        stacksets = self.stacksets.keys()
        for stackset in stacksets:
            if self.stacksets[stackset].name == name:
                self.stacksets[stackset].delete()

    def create_stack_instances(
        self, stackset_name, accounts, regions, parameters, operation_id=None
    ):
        stackset = self.get_stack_set(stackset_name)

        stackset.create_stack_instances(
            accounts=accounts,
            regions=regions,
            parameters=parameters,
            operation_id=operation_id,
        )
        return stackset

    def update_stack_set(
        self,
        stackset_name,
        template=None,
        description=None,
        parameters=None,
        tags=None,
        admin_role=None,
        execution_role=None,
        accounts=None,
        regions=None,
        operation_id=None,
    ):
        stackset = self.get_stack_set(stackset_name)
        update = stackset.update(
            template=template,
            description=description,
            parameters=parameters,
            tags=tags,
            admin_role=admin_role,
            execution_role=execution_role,
            accounts=accounts,
            regions=regions,
            operation_id=operation_id,
        )
        return update

    def delete_stack_instances(
        self, stackset_name, accounts, regions, operation_id=None
    ):
        stackset = self.get_stack_set(stackset_name)
        stackset.delete_stack_instances(accounts, regions, operation_id)
        return stackset

    def create_stack(
        self,
        name,
        template,
        parameters,
        region_name,
        notification_arns=None,
        tags=None,
        role_arn=None,
        create_change_set=False,
    ):
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

    def create_change_set(
        self,
        stack_name,
        change_set_name,
        template,
        parameters,
        region_name,
        change_set_type,
        notification_arns=None,
        tags=None,
        role_arn=None,
    ):
        stack_id = None
        stack_template = None
        if change_set_type == "UPDATE":
            stacks = self.stacks.values()
            stack = None
            for s in stacks:
                if s.name == stack_name:
                    stack = s
                    stack_id = stack.stack_id
                    stack_template = stack.template
            if stack is None:
                raise ValidationError(stack_name)
        else:
            stack_id = generate_stack_id(stack_name, region_name)
            stack_template = {}

        change_set_id = generate_changeset_id(change_set_name, region_name)
        new_change_set = FakeChangeSet(
            stack_id=stack_id,
            stack_name=stack_name,
            stack_template=stack_template,
            change_set_id=change_set_id,
            change_set_name=change_set_name,
            template=template,
            parameters=parameters,
            region_name=region_name,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
            cross_stack_resources=self.exports,
        )
        self.change_sets[change_set_id] = new_change_set
        self.stacks[stack_id] = new_change_set
        return change_set_id, stack_id

    def delete_change_set(self, change_set_name, stack_name=None):
        if change_set_name in self.change_sets:
            # This means arn was passed in
            del self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    del self.change_sets[cs]

    def describe_change_set(self, change_set_name, stack_name=None):
        change_set = None
        if change_set_name in self.change_sets:
            # This means arn was passed in
            change_set = self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    change_set = self.change_sets[cs]
        if change_set is None:
            raise ValidationError(change_set_name)
        return change_set

    def execute_change_set(self, change_set_name, stack_name=None):
        stack = None
        if change_set_name in self.change_sets:
            # This means arn was passed in
            stack = self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    stack = self.change_sets[cs]
        if stack is None:
            raise ValidationError(stack_name)
        if stack.events[-1].resource_status == "REVIEW_IN_PROGRESS":
            stack._add_stack_event(
                "CREATE_IN_PROGRESS", resource_status_reason="User Initiated"
            )
            stack._add_stack_event("CREATE_COMPLETE")
        else:
            stack._add_stack_event("UPDATE_IN_PROGRESS")
            stack._add_stack_event("UPDATE_COMPLETE")
        stack.create_resources()
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

    def list_change_sets(self):
        return self.change_sets.values()

    def list_stacks(self, status_filter=None):
        total_stacks = [v for v in self.stacks.values()] + [
            v for v in self.deleted_stacks.values()
        ]
        return filter_stacks(total_stacks, status_filter)

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
        if stack is None:
            return None
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
            next_token = "100" if len(all_exports) > 100 else None
        else:
            token = int(token)
            exports = all_exports[token : token + 100]
            next_token = str(token + 100) if len(all_exports) > token + 100 else None
        return exports, next_token

    def validate_template(self, template):
        return validate_template_cfn_lint(template)

    def _validate_export_uniqueness(self, stack):
        new_stack_export_names = [x.name for x in stack.exports]
        export_names = self.exports.keys()
        if not set(export_names).isdisjoint(new_stack_export_names):
            raise ValidationError(
                stack.stack_id,
                message="Export names must be unique across a given region",
            )


cloudformation_backends = {}
for region in Session().get_available_regions("cloudformation"):
    cloudformation_backends[region] = CloudFormationBackend()
for region in Session().get_available_regions(
    "cloudformation", partition_name="aws-us-gov"
):
    cloudformation_backends[region] = CloudFormationBackend()
for region in Session().get_available_regions(
    "cloudformation", partition_name="aws-cn"
):
    cloudformation_backends[region] = CloudFormationBackend()
