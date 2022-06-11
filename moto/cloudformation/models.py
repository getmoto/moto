from datetime import datetime, timedelta
import json
import yaml
import uuid

from collections import OrderedDict
from yaml.parser import ParserError  # pylint:disable=c-extension-no-member
from yaml.scanner import ScannerError  # pylint:disable=c-extension-no-member

from moto.core import BaseBackend, BaseModel, get_account_id
from moto.core.utils import (
    iso_8601_datetime_with_milliseconds,
    iso_8601_datetime_without_milliseconds,
    BackendDict,
)
from moto.sns.models import sns_backends

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

    def _create_operation(
        self, operation_id, action, status, accounts=None, regions=None
    ):
        accounts = accounts or []
        regions = regions or []
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

        self.instances.create_instances(accounts, regions, parameters)
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

    def create_instances(self, accounts, regions, parameters):
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
        self.policy = ""

        self.cross_stack_resources = cross_stack_resources or {}
        self.resource_map = self._create_resource_map()

        self.custom_resources = dict()

        self.output_map = self._create_output_map()
        self.creation_time = datetime.utcnow()
        self.status = "CREATE_PENDING"

    def has_template(self, other_template):
        our_template = (
            self.template
            if isinstance(self.template, dict)
            else json.loads(self.template)
        )
        return our_template == json.loads(other_template)

    def has_parameters(self, other_parameters):
        return self.parameters == other_parameters

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
        return OutputMap(self.resource_map, self.template_dict, self.stack_id)

    @property
    def creation_time_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.creation_time)

    def _add_stack_event(
        self, resource_status, resource_status_reason=None, resource_properties=None
    ):

        event = FakeEvent(
            stack_id=self.stack_id,
            stack_name=self.name,
            logical_resource_id=self.name,
            physical_resource_id=self.stack_id,
            resource_type="AWS::CloudFormation::Stack",
            resource_status=resource_status,
            resource_status_reason=resource_status_reason,
            resource_properties=resource_properties,
        )

        event.sendToSns(self.region_name, self.notification_arns)
        self.events.append(event)

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
        except (ParserError, ScannerError):
            self.template_dict = json.loads(self.template)

    @property
    def stack_parameters(self):
        return self.resource_map.resolved_parameters

    @property
    def stack_resources(self):
        return self.resource_map.values()

    @property
    def stack_outputs(self):
        return [v for v in self.output_map.values() if v]

    @property
    def exports(self):
        return self.output_map.exports

    def add_custom_resource(self, custom_resource):
        self.custom_resources[custom_resource.logical_id] = custom_resource

    def get_custom_resource(self, custom_resource):
        return self.custom_resources[custom_resource]

    def create_resources(self):
        self.status = "CREATE_IN_PROGRESS"
        all_resources_ready = self.resource_map.create(self.template_dict)
        # Set the description of the stack
        self.description = self.template_dict.get("Description")
        if all_resources_ready:
            self.mark_creation_complete()

    def verify_readiness(self):
        if self.resource_map.creation_complete():
            self.mark_creation_complete()

    def mark_creation_complete(self):
        self.status = "CREATE_COMPLETE"
        self._add_stack_event("CREATE_COMPLETE")

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


class FakeChangeSet(BaseModel):
    def __init__(
        self,
        change_set_type,
        change_set_id,
        change_set_name,
        stack,
        template,
        parameters,
        description,
        notification_arns=None,
        tags=None,
        role_arn=None,
    ):
        self.change_set_type = change_set_type
        self.change_set_id = change_set_id
        self.change_set_name = change_set_name

        self.stack = stack
        self.stack_id = self.stack.stack_id
        self.stack_name = self.stack.name
        self.notification_arns = notification_arns
        self.description = description
        self.tags = tags
        self.role_arn = role_arn
        self.template = template
        self.parameters = parameters
        self._parse_template()

        self.creation_time = datetime.utcnow()
        self.changes = self.diff()

    def _parse_template(self):
        yaml.add_multi_constructor("", yaml_tag_constructor)
        try:
            self.template_dict = yaml.load(self.template, Loader=yaml.Loader)
        except (ParserError, ScannerError):
            self.template_dict = json.loads(self.template)

    @property
    def creation_time_iso_8601(self):
        return iso_8601_datetime_without_milliseconds(self.creation_time)

    def diff(self):
        changes = []
        resources_by_action = self.stack.resource_map.build_change_set_actions(
            self.template_dict, self.parameters
        )
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

    def apply(self):
        self.stack.resource_map.update(self.template_dict, self.parameters)


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
        client_request_token=None,
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
        self.client_request_token = client_request_token

    def sendToSns(self, region, sns_topic_arns):
        message = """StackId='{stack_id}'
Timestamp='{timestamp}'
EventId='{event_id}'
LogicalResourceId='{logical_resource_id}'
Namespace='{account_id}'
ResourceProperties='{resource_properties}'
ResourceStatus='{resource_status}'
ResourceStatusReason='{resource_status_reason}'
ResourceType='{resource_type}'
StackName='{stack_name}'
ClientRequestToken='{client_request_token}'""".format(
            stack_id=self.stack_id,
            timestamp=iso_8601_datetime_with_milliseconds(self.timestamp),
            event_id=self.event_id,
            logical_resource_id=self.logical_resource_id,
            account_id=get_account_id(),
            resource_properties=self.resource_properties,
            resource_status=self.resource_status,
            resource_status_reason=self.resource_status_reason,
            resource_type=self.resource_type,
            stack_name=self.stack_name,
            client_request_token=self.client_request_token,
        )

        for sns_topic_arn in sns_topic_arns:
            sns_backends[region].publish(
                message, subject="AWS CloudFormation Notification", arn=sns_topic_arn
            )


def filter_stacks(all_stacks, status_filter):
    filtered_stacks = []
    if not status_filter:
        return all_stacks
    for stack in all_stacks:
        if stack.status in status_filter:
            filtered_stacks.append(stack)
    return filtered_stacks


class CloudFormationBackend(BaseBackend):
    """
    CustomResources are supported when running Moto in ServerMode.
    Because creating these resources involves running a Lambda-function that informs the MotoServer about the status of the resources, the MotoServer has to be reachable for outside connections.
    This means it has to run inside a Docker-container, or be started using `moto_server -h 0.0.0.0`.
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.stacks = OrderedDict()
        self.stacksets = OrderedDict()
        self.deleted_stacks = {}
        self.exports = OrderedDict()
        self.change_sets = OrderedDict()

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "cloudformation", policy_supported=False
        )

    def _resolve_update_parameters(self, instance, incoming_params):
        parameters = dict(
            [
                (parameter["parameter_key"], parameter["parameter_value"])
                for parameter in incoming_params
                if "parameter_value" in parameter
            ]
        )
        previous = dict(
            [
                (
                    parameter["parameter_key"],
                    instance.parameters[parameter["parameter_key"]],
                )
                for parameter in incoming_params
                if "use_previous_value" in parameter
            ]
        )
        parameters.update(previous)

        return parameters

    def create_stack_set(
        self,
        name,
        template,
        parameters,
        tags=None,
        description=None,
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
        if name in stacksets:
            return self.stacksets[name]
        for stackset in stacksets:
            if self.stacksets[stackset].name == name:
                return self.stacksets[stackset]
        raise ValidationError(name)

    def delete_stack_set(self, name):
        stacksets = self.stacksets.keys()
        if name in stacksets:
            self.stacksets[name].delete()
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
        resolved_parameters = self._resolve_update_parameters(
            instance=stackset, incoming_params=parameters
        )
        update = stackset.update(
            template=template,
            description=description,
            parameters=resolved_parameters,
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
        notification_arns=None,
        tags=None,
        role_arn=None,
    ):
        stack_id = generate_stack_id(name, self.region_name)
        new_stack = FakeStack(
            stack_id=stack_id,
            name=name,
            template=template,
            parameters=parameters,
            region_name=self.region_name,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
            cross_stack_resources=self.exports,
        )
        self.stacks[stack_id] = new_stack
        self._validate_export_uniqueness(new_stack)
        for export in new_stack.exports:
            self.exports[export.name] = export
        new_stack._add_stack_event(
            "CREATE_IN_PROGRESS", resource_status_reason="User Initiated"
        )
        new_stack.create_resources()
        return new_stack

    def create_change_set(
        self,
        stack_name,
        change_set_name,
        template,
        parameters,
        description,
        change_set_type,
        notification_arns=None,
        tags=None,
        role_arn=None,
    ):
        if change_set_type == "UPDATE":
            for stack in self.stacks.values():
                if stack.name == stack_name:
                    break
            else:
                raise ValidationError(stack_name)
        else:
            stack_id = generate_stack_id(stack_name, self.region_name)
            stack = FakeStack(
                stack_id=stack_id,
                name=stack_name,
                template={},
                parameters=parameters,
                region_name=self.region_name,
                notification_arns=notification_arns,
                tags=tags,
                role_arn=role_arn,
            )
            self.stacks[stack_id] = stack
            stack.status = "REVIEW_IN_PROGRESS"
            stack._add_stack_event(
                "REVIEW_IN_PROGRESS", resource_status_reason="User Initiated"
            )

        change_set_id = generate_changeset_id(change_set_name, self.region_name)

        new_change_set = FakeChangeSet(
            change_set_type=change_set_type,
            change_set_id=change_set_id,
            change_set_name=change_set_name,
            stack=stack,
            template=template,
            parameters=parameters,
            description=description,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
        )
        if (
            change_set_type == "UPDATE"
            and stack.has_template(template)
            and stack.has_parameters(parameters)
        ):
            # Nothing has changed - mark it as such
            new_change_set.status = "FAILED"
            new_change_set.execution_status = "UNAVAILABLE"
            new_change_set.status_reason = "The submitted information didn't contain changes. Submit different information to create a change set."
        else:
            new_change_set.status = "CREATE_COMPLETE"
            new_change_set.execution_status = "AVAILABLE"
        self.change_sets[change_set_id] = new_change_set
        return change_set_id, stack.stack_id

    def delete_change_set(self, change_set_name):
        if change_set_name in self.change_sets:
            # This means arn was passed in
            del self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    to_delete = cs
                    break
            del self.change_sets[to_delete]

    def describe_change_set(self, change_set_name):
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
        if change_set_name in self.change_sets:
            # This means arn was passed in
            change_set = self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    change_set = self.change_sets[cs]

        if change_set is None:
            raise ValidationError(stack_name)

        stack = self.stacks[change_set.stack_id]
        # TODO: handle execution errors and implement rollback
        if change_set.change_set_type == "CREATE":
            stack._add_stack_event(
                "CREATE_IN_PROGRESS", resource_status_reason="User Initiated"
            )
            change_set.apply()
            stack._add_stack_event("CREATE_COMPLETE")
        else:
            stack._add_stack_event("UPDATE_IN_PROGRESS")
            change_set.apply()
            stack._add_stack_event("UPDATE_COMPLETE")

        # set the execution status of the changeset
        change_set.execution_status = "EXECUTE_COMPLETE"

        # set the status of the stack
        stack.status = f"{change_set.change_set_type}_COMPLETE"
        stack.template = change_set.template
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
            raise ValidationError(name_or_stack_id)

    def update_stack(self, name, template, role_arn=None, parameters=None, tags=None):
        stack = self.get_stack(name)
        resolved_parameters = self._resolve_update_parameters(
            instance=stack, incoming_params=parameters
        )
        stack.update(template, role_arn, parameters=resolved_parameters, tags=tags)
        return stack

    def get_stack_policy(self, stack_name):
        try:
            stack = self.get_stack(stack_name)
        except ValidationError:
            raise ValidationError(message=f"Stack: {stack_name} does not exist")
        return stack.policy

    def set_stack_policy(self, stack_name, policy_body):
        """
        Note that Moto does no validation/parsing/enforcement of this policy - we simply persist it.
        """
        try:
            stack = self.get_stack(stack_name)
        except ValidationError:
            raise ValidationError(message=f"Stack: {stack_name} does not exist")
        stack.policy = policy_body

    def list_stack_resources(self, stack_name_or_id):
        stack = self.get_stack(stack_name_or_id)
        return stack.stack_resources

    def delete_stack(self, name_or_stack_id):
        if name_or_stack_id in self.stacks:
            # Delete by stack id
            stack = self.stacks.pop(name_or_stack_id, None)
            export_names = [export.name for export in stack.exports]
            stack.delete()
            self.deleted_stacks[stack.stack_id] = stack
            for export_name in export_names:
                self.exports.pop(export_name)
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


cloudformation_backends = BackendDict(CloudFormationBackend, "cloudformation")
