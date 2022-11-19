from datetime import datetime, timedelta
import json
import yaml

from collections import OrderedDict
from typing import Any, Dict, List, Optional, Iterable, Tuple, Union, Type
from yaml.parser import ParserError  # pylint:disable=c-extension-no-member
from yaml.scanner import ScannerError  # pylint:disable=c-extension-no-member

from moto.core import BaseBackend, BackendDict, BaseModel, CloudFormationModel
from moto.core.utils import (
    iso_8601_datetime_with_milliseconds,
    iso_8601_datetime_without_milliseconds,
)
from moto.moto_api._internal import mock_random
from moto.sns.models import sns_backends

from .custom_model import CustomModel
from .parsing import ResourceMap, Output, OutputMap, Export
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
        stackset_id: str,
        account_id: str,
        name: str,
        template: str,
        region: str,
        description: Optional[str],
        parameters: Dict[str, str],
        tags: Optional[Dict[str, str]] = None,
        admin_role: str = "AWSCloudFormationStackSetAdministrationRole",
        execution_role: str = "AWSCloudFormationStackSetExecutionRole",
    ):
        self.id = stackset_id
        self.arn = generate_stackset_arn(stackset_id, region, account_id)
        self.name = name
        self.template = template
        self.description = description
        self.parameters = parameters
        self.tags = tags
        self.admin_role = admin_role
        self.admin_role_arn = f"arn:aws:iam::{account_id}:role/{self.admin_role}"
        self.execution_role = execution_role
        self.status = "ACTIVE"
        self.instances = FakeStackInstances(parameters, self.id, self.name)
        self.stack_instances = self.instances.stack_instances
        self.operations: List[Dict[str, Any]] = []

    def _create_operation(
        self,
        operation_id: str,
        action: str,
        status: str,
        accounts: Optional[List[str]] = None,
        regions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        accounts = accounts or []
        regions = regions or []
        operation = {
            "OperationId": operation_id,
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

    def get_operation(self, operation_id: str) -> Dict[str, Any]:
        for operation in self.operations:
            if operation_id == operation["OperationId"]:
                return operation
        raise ValidationError(operation_id)

    def update_operation(self, operation_id: str, status: str) -> str:
        operation = self.get_operation(operation_id)
        operation["Status"] = status
        return operation_id

    def delete(self) -> None:
        self.status = "DELETED"

    def update(
        self,
        template: str,
        description: str,
        parameters: Dict[str, str],
        tags: Dict[str, str],
        admin_role: str,
        execution_role: str,
        accounts: List[str],
        regions: List[str],
        operation_id: str,
    ) -> Dict[str, Any]:

        self.template = template or self.template
        self.description = description if description is not None else self.description
        self.parameters = parameters or self.parameters
        self.tags = tags or self.tags
        self.admin_role = admin_role or self.admin_role
        self.execution_role = execution_role or self.execution_role

        if accounts and regions:
            self.update_instances(accounts, regions, self.parameters)  # type: ignore[arg-type]

        operation = self._create_operation(
            operation_id=operation_id,
            action="UPDATE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )
        return operation

    def create_stack_instances(
        self, accounts: List[str], regions: List[str], parameters: List[Dict[str, Any]]
    ) -> None:
        operation_id = str(mock_random.uuid4())
        if not parameters:
            parameters = self.parameters  # type: ignore[assignment]

        self.instances.create_instances(accounts, regions, parameters)
        self._create_operation(
            operation_id=operation_id,
            action="CREATE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )

    def delete_stack_instances(self, accounts: List[str], regions: List[str]) -> None:
        operation_id = str(mock_random.uuid4())

        self.instances.delete(accounts, regions)

        self._create_operation(
            operation_id=operation_id,
            action="DELETE",
            status="SUCCEEDED",
            accounts=accounts,
            regions=regions,
        )

    def update_instances(
        self, accounts: List[str], regions: List[str], parameters: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        operation_id = str(mock_random.uuid4())

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
    def __init__(
        self, parameters: Dict[str, str], stackset_id: str, stackset_name: str
    ):
        self.parameters = parameters or {}
        self.stackset_id = stackset_id
        self.stack_name = f"StackSet-{stackset_id}"
        self.stackset_name = stackset_name
        self.stack_instances: List[Dict[str, Any]] = []

    def create_instances(
        self,
        accounts: List[str],
        regions: List[str],
        parameters: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        new_instances = []
        for region in regions:
            for account in accounts:
                instance = {
                    "StackId": generate_stack_id(self.stack_name, region, account),
                    "StackSetId": self.stackset_id,
                    "Region": region,
                    "Account": account,
                    "Status": "CURRENT",
                    "ParameterOverrides": parameters or [],
                }
                new_instances.append(instance)
        self.stack_instances += new_instances
        return new_instances

    def update(
        self,
        accounts: List[str],
        regions: List[str],
        parameters: Optional[List[Dict[str, Any]]],
    ) -> Any:
        for account in accounts:
            for region in regions:
                instance = self.get_instance(account, region)
                if parameters:
                    instance["ParameterOverrides"] = parameters
                else:
                    instance["ParameterOverrides"] = []

    def delete(self, accounts: List[str], regions: List[str]) -> None:
        for i, instance in enumerate(self.stack_instances):
            if instance["Region"] in regions and instance["Account"] in accounts:
                self.stack_instances.pop(i)

    def get_instance(self, account: str, region: str) -> Dict[str, Any]:  # type: ignore[return]
        for i, instance in enumerate(self.stack_instances):
            if instance["Region"] == region and instance["Account"] == account:
                return self.stack_instances[i]


class FakeStack(BaseModel):
    def __init__(
        self,
        stack_id: str,
        name: str,
        template: Union[str, Dict[str, Any]],
        parameters: Dict[str, str],
        account_id: str,
        region_name: str,
        notification_arns: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        role_arn: Optional[str] = None,
        cross_stack_resources: Optional[Dict[str, Export]] = None,
        enable_termination_protection: Optional[bool] = False,
    ):
        self.stack_id = stack_id
        self.name = name
        self.account_id = account_id
        self.template = template
        if template != {}:
            self._parse_template()
            self.description = self.template_dict.get("Description")
        else:
            self.template_dict: Dict[str, Any] = {}
            self.description = None
        self.parameters = parameters
        self.region_name = region_name
        self.notification_arns = notification_arns if notification_arns else []
        self.role_arn = role_arn
        self.tags = tags if tags else {}
        self.events: List[FakeEvent] = []
        self.policy = ""

        self.cross_stack_resources: Dict[str, Export] = cross_stack_resources or {}
        self.enable_termination_protection: bool = (
            enable_termination_protection or False
        )
        self.resource_map = self._create_resource_map()

        self.custom_resources: Dict[str, CustomModel] = dict()

        self.output_map = self._create_output_map()
        self.creation_time = datetime.utcnow()
        self.status = "CREATE_PENDING"

    def has_template(self, other_template: str) -> bool:
        our_template = (
            self.template
            if isinstance(self.template, dict)
            else json.loads(self.template)
        )
        return our_template == json.loads(other_template)

    def has_parameters(self, other_parameters: Dict[str, Any]) -> bool:
        return self.parameters == other_parameters

    def _create_resource_map(self) -> ResourceMap:
        resource_map = ResourceMap(
            self.stack_id,
            self.name,
            self.parameters,
            self.tags,
            account_id=self.account_id,
            region_name=self.region_name,
            template=self.template_dict,
            cross_stack_resources=self.cross_stack_resources,
        )
        resource_map.load()
        return resource_map

    def _create_output_map(self) -> OutputMap:
        return OutputMap(self.resource_map, self.template_dict, self.stack_id)

    @property
    def creation_time_iso_8601(self) -> str:
        return iso_8601_datetime_without_milliseconds(self.creation_time)  # type: ignore[return-value]

    def _add_stack_event(
        self,
        resource_status: str,
        resource_status_reason: Optional[str] = None,
        resource_properties: Optional[str] = None,
    ) -> None:

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

        event.sendToSns(self.account_id, self.region_name, self.notification_arns)
        self.events.append(event)

    def _parse_template(self) -> None:
        yaml.add_multi_constructor("", yaml_tag_constructor)
        try:
            self.template_dict = yaml.load(self.template, Loader=yaml.Loader)  # type: ignore[arg-type]
        except (ParserError, ScannerError):
            self.template_dict = json.loads(self.template)  # type: ignore[arg-type]

    @property
    def stack_parameters(self) -> Dict[str, Any]:  # type: ignore[misc]
        return self.resource_map.resolved_parameters

    @property
    def stack_resources(self) -> Iterable[Type[CloudFormationModel]]:
        return self.resource_map.values()

    @property
    def stack_outputs(self) -> List[Output]:
        return [v for v in self.output_map.values() if v]

    @property
    def exports(self) -> List[Export]:
        return self.output_map.exports

    def add_custom_resource(self, custom_resource: CustomModel) -> None:
        self.custom_resources[custom_resource.logical_id] = custom_resource

    def get_custom_resource(self, custom_resource: str) -> CustomModel:
        return self.custom_resources[custom_resource]

    def create_resources(self) -> None:
        self.status = "CREATE_IN_PROGRESS"
        all_resources_ready = self.resource_map.create(self.template_dict)
        # Set the description of the stack
        self.description = self.template_dict.get("Description")
        if all_resources_ready:
            self.mark_creation_complete()

    def verify_readiness(self) -> None:
        if self.resource_map.creation_complete():
            self.mark_creation_complete()

    def mark_creation_complete(self) -> None:
        self.status = "CREATE_COMPLETE"
        self._add_stack_event("CREATE_COMPLETE")

    def update(
        self,
        template: str,
        role_arn: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> None:
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

    def delete(self) -> None:
        self._add_stack_event(
            "DELETE_IN_PROGRESS", resource_status_reason="User Initiated"
        )
        self.resource_map.delete()
        self._add_stack_event("DELETE_COMPLETE")
        self.status = "DELETE_COMPLETE"


class FakeChange(BaseModel):
    def __init__(self, action: str, logical_resource_id: str, resource_type: str):
        self.action = action
        self.logical_resource_id = logical_resource_id
        self.resource_type = resource_type


class FakeChangeSet(BaseModel):
    def __init__(
        self,
        change_set_type: str,
        change_set_id: str,
        change_set_name: str,
        stack: FakeStack,
        template: str,
        parameters: Dict[str, str],
        description: str,
        notification_arns: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        role_arn: Optional[str] = None,
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

        self.status: Optional[str] = None
        self.execution_status: Optional[str] = None
        self.status_reason: Optional[str] = None

    def _parse_template(self) -> None:
        yaml.add_multi_constructor("", yaml_tag_constructor)
        try:
            self.template_dict = yaml.load(self.template, Loader=yaml.Loader)
        except (ParserError, ScannerError):
            self.template_dict = json.loads(self.template)

    @property
    def creation_time_iso_8601(self) -> str:
        return iso_8601_datetime_without_milliseconds(self.creation_time)  # type: ignore[return-value]

    def diff(self) -> List[FakeChange]:
        changes = []
        resources_by_action = self.stack.resource_map.build_change_set_actions(
            self.template_dict
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

    def apply(self) -> None:
        self.stack.resource_map.update(self.template_dict, self.parameters)


class FakeEvent(BaseModel):
    def __init__(
        self,
        stack_id: str,
        stack_name: str,
        logical_resource_id: str,
        physical_resource_id: str,
        resource_type: str,
        resource_status: str,
        resource_status_reason: Optional[str],
        resource_properties: Optional[str],
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
        self.event_id = mock_random.uuid4()
        self.client_request_token = None

    def sendToSns(
        self, account_id: str, region: str, sns_topic_arns: List[str]
    ) -> None:
        message = f"""StackId='{self.stack_id}'
Timestamp='{iso_8601_datetime_with_milliseconds(self.timestamp)}'
EventId='{self.event_id}'
LogicalResourceId='{self.logical_resource_id}'
Namespace='{account_id}'
ResourceProperties='{self.resource_properties}'
ResourceStatus='{self.resource_status}'
ResourceStatusReason='{self.resource_status_reason}'
ResourceType='{self.resource_type}'
StackName='{self.stack_name}'
ClientRequestToken='{self.client_request_token}'"""

        for sns_topic_arn in sns_topic_arns:
            sns_backends[account_id][region].publish(
                message, subject="AWS CloudFormation Notification", arn=sns_topic_arn
            )


def filter_stacks(
    all_stacks: List[FakeStack], status_filter: Optional[List[str]]
) -> List[FakeStack]:
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

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.stacks: Dict[str, FakeStack] = OrderedDict()
        self.stacksets: Dict[str, FakeStackSet] = OrderedDict()
        self.deleted_stacks: Dict[str, FakeStack] = {}
        self.exports: Dict[str, Export] = OrderedDict()
        self.change_sets: Dict[str, FakeChangeSet] = OrderedDict()

    @staticmethod
    def default_vpc_endpoint_service(
        service_region: str, zones: List[str]
    ) -> List[Dict[str, str]]:
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "cloudformation", policy_supported=False
        )

    def _resolve_update_parameters(
        self,
        instance: Union[FakeStack, FakeStackSet],
        incoming_params: List[Dict[str, str]],
    ) -> Dict[str, str]:
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
        name: str,
        template: str,
        parameters: Dict[str, str],
        tags: Dict[str, str],
    ) -> FakeStackSet:
        stackset_id = generate_stackset_id(name)
        new_stackset = FakeStackSet(
            stackset_id=stackset_id,
            account_id=self.account_id,
            name=name,
            region=self.region_name,
            template=template,
            parameters=parameters,
            description=None,
            tags=tags,
        )
        self.stacksets[stackset_id] = new_stackset
        return new_stackset

    def get_stack_set(self, name: str) -> FakeStackSet:
        stacksets = self.stacksets.keys()
        if name in stacksets:
            return self.stacksets[name]
        for stackset in stacksets:
            if self.stacksets[stackset].name == name:
                return self.stacksets[stackset]
        raise ValidationError(name)

    def delete_stack_set(self, name: str) -> None:
        stacksets = self.stacksets.keys()
        if name in stacksets:
            self.stacksets[name].delete()
        for stackset in stacksets:
            if self.stacksets[stackset].name == name:
                self.stacksets[stackset].delete()

    def create_stack_instances(
        self,
        stackset_name: str,
        accounts: List[str],
        regions: List[str],
        parameters: List[Dict[str, str]],
    ) -> FakeStackSet:
        stackset = self.get_stack_set(stackset_name)

        stackset.create_stack_instances(
            accounts=accounts,
            regions=regions,
            parameters=parameters,
        )
        return stackset

    def update_stack_instances(
        self,
        stackset_name: str,
        accounts: List[str],
        regions: List[str],
        parameters: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        stack_set = self.get_stack_set(stackset_name)
        return stack_set.update_instances(accounts, regions, parameters)

    def update_stack_set(
        self,
        stackset_name: str,
        template: str,
        description: str,
        parameters: List[Dict[str, str]],
        tags: Dict[str, str],
        admin_role: str,
        execution_role: str,
        accounts: List[str],
        regions: List[str],
        operation_id: str,
    ) -> Dict[str, Any]:
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
        self, stackset_name: str, accounts: List[str], regions: List[str]
    ) -> FakeStackSet:
        stackset = self.get_stack_set(stackset_name)
        stackset.delete_stack_instances(accounts, regions)
        return stackset

    def create_stack(
        self,
        name: str,
        template: str,
        parameters: Dict[str, Any],
        notification_arns: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        role_arn: Optional[str] = None,
        enable_termination_protection: Optional[bool] = False,
    ) -> FakeStack:
        """
        The functionality behind EnableTerminationProtection is not yet implemented.
        """
        stack_id = generate_stack_id(name, self.region_name, self.account_id)
        new_stack = FakeStack(
            stack_id=stack_id,
            name=name,
            template=template,
            parameters=parameters,
            account_id=self.account_id,
            region_name=self.region_name,
            notification_arns=notification_arns,
            tags=tags,
            role_arn=role_arn,
            cross_stack_resources=self.exports,
            enable_termination_protection=enable_termination_protection,
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
        stack_name: str,
        change_set_name: str,
        template: str,
        parameters: Dict[str, str],
        description: str,
        change_set_type: str,
        notification_arns: Optional[List[str]] = None,
        tags: Optional[Dict[str, str]] = None,
        role_arn: Optional[str] = None,
    ) -> Tuple[str, str]:
        if change_set_type == "UPDATE":
            for stack in self.stacks.values():
                if stack.name == stack_name:
                    break
            else:
                raise ValidationError(stack_name)
        else:
            stack_id = generate_stack_id(stack_name, self.region_name, self.account_id)
            stack = FakeStack(
                stack_id=stack_id,
                name=stack_name,
                template={},
                parameters=parameters,
                account_id=self.account_id,
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

        change_set_id = generate_changeset_id(
            change_set_name, self.region_name, self.account_id
        )

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

    def delete_change_set(self, change_set_name: str) -> None:
        if change_set_name in self.change_sets:
            # This means arn was passed in
            del self.change_sets[change_set_name]
        else:
            for cs in self.change_sets:
                if self.change_sets[cs].change_set_name == change_set_name:
                    to_delete = cs
                    break
            del self.change_sets[to_delete]

    def describe_change_set(self, change_set_name: str) -> Optional[FakeChangeSet]:
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

    def execute_change_set(
        self, change_set_name: str, stack_name: Optional[str] = None
    ) -> None:
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

    def describe_stacks(self, name_or_stack_id: str) -> List[FakeStack]:
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

    def list_change_sets(self) -> Iterable[FakeChangeSet]:
        return self.change_sets.values()

    def list_stacks(self, status_filter: Optional[List[str]] = None) -> List[FakeStack]:
        total_stacks = [v for v in self.stacks.values()] + [
            v for v in self.deleted_stacks.values()
        ]
        return filter_stacks(total_stacks, status_filter)

    def get_stack(self, name_or_stack_id: str) -> FakeStack:
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

    def update_stack(
        self,
        name: str,
        template: str,
        role_arn: Optional[str],
        parameters: List[Dict[str, Any]],
        tags: Optional[Dict[str, str]],
    ) -> FakeStack:
        stack = self.get_stack(name)
        resolved_parameters = self._resolve_update_parameters(
            instance=stack, incoming_params=parameters
        )
        stack.update(template, role_arn, parameters=resolved_parameters, tags=tags)
        return stack

    def get_stack_policy(self, stack_name: str) -> str:
        try:
            stack = self.get_stack(stack_name)
        except ValidationError:
            raise ValidationError(message=f"Stack: {stack_name} does not exist")
        return stack.policy

    def set_stack_policy(self, stack_name: str, policy_body: str) -> None:
        """
        Note that Moto does no validation/parsing/enforcement of this policy - we simply persist it.
        """
        try:
            stack = self.get_stack(stack_name)
        except ValidationError:
            raise ValidationError(message=f"Stack: {stack_name} does not exist")
        stack.policy = policy_body

    def list_stack_resources(
        self, stack_name_or_id: str
    ) -> Iterable[Type[CloudFormationModel]]:
        stack = self.get_stack(stack_name_or_id)
        return stack.stack_resources

    def delete_stack(self, name_or_stack_id: str) -> None:
        if name_or_stack_id in self.stacks:
            # Delete by stack id
            stack = self.stacks.pop(name_or_stack_id)
            export_names = [export.name for export in stack.exports]
            stack.delete()
            self.deleted_stacks[stack.stack_id] = stack
            for export_name in export_names:
                self.exports.pop(export_name)
            self.stacks.pop(name_or_stack_id, None)
        else:
            # Delete by stack name
            for stack in list(self.stacks.values()):
                if stack.name == name_or_stack_id:
                    self.delete_stack(stack.stack_id)

    def list_exports(
        self, tokenstr: Optional[str]
    ) -> Tuple[List[Export], Optional[str]]:
        all_exports = list(self.exports.values())
        if tokenstr is None:
            exports = all_exports[0:100]
            next_token = "100" if len(all_exports) > 100 else None
        else:
            token = int(tokenstr)
            exports = all_exports[token : token + 100]
            next_token = str(token + 100) if len(all_exports) > token + 100 else None
        return exports, next_token

    def validate_template(self, template: str) -> List[Any]:
        return validate_template_cfn_lint(template)

    def _validate_export_uniqueness(self, stack: FakeStack) -> None:
        new_stack_export_names = [x.name for x in stack.exports]
        export_names = self.exports.keys()
        if not set(export_names).isdisjoint(new_stack_export_names):
            raise ValidationError(
                stack.stack_id,
                message="Export names must be unique across a given region",
            )


cloudformation_backends = BackendDict(CloudFormationBackend, "cloudformation")
