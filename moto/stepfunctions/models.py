import json
import re
from datetime import datetime
from dateutil.tz import tzlocal

from moto.core import BaseBackend, CloudFormationModel
from moto.core.utils import iso_8601_datetime_with_milliseconds, BackendDict
from uuid import uuid4
from .exceptions import (
    ExecutionAlreadyExists,
    ExecutionDoesNotExist,
    InvalidArn,
    InvalidExecutionInput,
    InvalidName,
    ResourceNotFound,
    StateMachineDoesNotExist,
)
from .utils import api_to_cfn_tags, cfn_to_api_tags, PAGINATION_MODEL
from moto import settings
from moto.utilities.paginator import paginate


class StateMachine(CloudFormationModel):
    def __init__(self, arn, name, definition, roleArn, tags=None):
        self.creation_date = iso_8601_datetime_with_milliseconds(datetime.now())
        self.update_date = self.creation_date
        self.arn = arn
        self.name = name
        self.definition = definition
        self.roleArn = roleArn
        self.executions = []
        self.tags = []
        if tags:
            self.add_tags(tags)

    def start_execution(self, region_name, account_id, execution_name, execution_input):
        self._ensure_execution_name_doesnt_exist(execution_name)
        self._validate_execution_input(execution_input)
        execution = Execution(
            region_name=region_name,
            account_id=account_id,
            state_machine_name=self.name,
            execution_name=execution_name,
            state_machine_arn=self.arn,
            execution_input=execution_input,
        )
        self.executions.append(execution)
        return execution

    def stop_execution(self, execution_arn):
        execution = next(
            (x for x in self.executions if x.execution_arn == execution_arn), None
        )
        if not execution:
            raise ExecutionDoesNotExist(
                "Execution Does Not Exist: '" + execution_arn + "'"
            )
        execution.stop()
        return execution

    def _ensure_execution_name_doesnt_exist(self, name):
        for execution in self.executions:
            if execution.name == name:
                raise ExecutionAlreadyExists(
                    "Execution Already Exists: '" + execution.execution_arn + "'"
                )

    def _validate_execution_input(self, execution_input):
        try:
            json.loads(execution_input)
        except Exception as ex:
            raise InvalidExecutionInput(
                "Invalid State Machine Execution Input: '" + str(ex) + "'"
            )

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if value is not None:
                setattr(self, key, value)
        self.update_date = iso_8601_datetime_with_milliseconds(datetime.now())

    def add_tags(self, tags):
        merged_tags = []
        for tag in self.tags:
            replacement_index = next(
                (index for (index, d) in enumerate(tags) if d["key"] == tag["key"]),
                None,
            )
            if replacement_index is not None:
                replacement = tags.pop(replacement_index)
                merged_tags.append(replacement)
            else:
                merged_tags.append(tag)
        for tag in tags:
            merged_tags.append(tag)
        self.tags = merged_tags
        return self.tags

    def remove_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["key"] not in tag_keys]
        return self.tags

    @property
    def physical_resource_id(self):
        return self.arn

    def get_cfn_properties(self, prop_overrides):
        property_names = [
            "DefinitionString",
            "RoleArn",
            "StateMachineName",
        ]
        properties = {}
        for prop in property_names:
            properties[prop] = prop_overrides.get(prop, self.get_cfn_attribute(prop))
        # Special handling for Tags
        overridden_keys = [tag["Key"] for tag in prop_overrides.get("Tags", [])]
        original_tags_to_include = [
            tag
            for tag in self.get_cfn_attribute("Tags")
            if tag["Key"] not in overridden_keys
        ]
        properties["Tags"] = original_tags_to_include + prop_overrides.get("Tags", [])
        return properties

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in [
            "Name",
            "DefinitionString",
            "RoleArn",
            "StateMachineName",
            "Tags",
        ]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "Name":
            return self.name
        elif attribute_name == "DefinitionString":
            return self.definition
        elif attribute_name == "RoleArn":
            return self.roleArn
        elif attribute_name == "StateMachineName":
            return self.name
        elif attribute_name == "Tags":
            return api_to_cfn_tags(self.tags)

        raise UnformattedGetAttTemplateException()

    @staticmethod
    def cloudformation_name_type():
        return "StateMachine"

    @staticmethod
    def cloudformation_type():
        return "AWS::StepFunctions::StateMachine"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, account_id, region_name, **kwargs
    ):
        properties = cloudformation_json["Properties"]
        name = properties.get("StateMachineName", resource_name)
        definition = properties.get("DefinitionString", "")
        role_arn = properties.get("RoleArn", "")
        tags = cfn_to_api_tags(properties.get("Tags", []))
        sf_backend = stepfunction_backends[account_id][region_name]
        return sf_backend.create_state_machine(name, definition, role_arn, tags=tags)

    @classmethod
    def delete_from_cloudformation_json(cls, resource_name, _, account_id, region_name):
        sf_backend = stepfunction_backends[account_id][region_name]
        sf_backend.delete_state_machine(resource_name)

    @classmethod
    def update_from_cloudformation_json(
        cls,
        original_resource,
        new_resource_name,
        cloudformation_json,
        account_id,
        region_name,
    ):
        properties = cloudformation_json.get("Properties", {})
        name = properties.get("StateMachineName", original_resource.name)

        if name != original_resource.name:
            # Replacement
            new_properties = original_resource.get_cfn_properties(properties)
            cloudformation_json["Properties"] = new_properties
            new_resource = cls.create_from_cloudformation_json(
                name, cloudformation_json, account_id, region_name
            )
            cls.delete_from_cloudformation_json(
                original_resource.arn, cloudformation_json, account_id, region_name
            )
            return new_resource

        else:
            # No Interruption
            definition = properties.get("DefinitionString")
            role_arn = properties.get("RoleArn")
            tags = cfn_to_api_tags(properties.get("Tags", []))
            sf_backend = stepfunction_backends[account_id][region_name]
            state_machine = sf_backend.update_state_machine(
                original_resource.arn, definition=definition, role_arn=role_arn
            )
            state_machine.add_tags(tags)
            return state_machine


class Execution:
    def __init__(
        self,
        region_name,
        account_id,
        state_machine_name,
        execution_name,
        state_machine_arn,
        execution_input,
    ):
        execution_arn = "arn:aws:states:{}:{}:execution:{}:{}"
        execution_arn = execution_arn.format(
            region_name, account_id, state_machine_name, execution_name
        )
        self.execution_arn = execution_arn
        self.name = execution_name
        self.start_date = iso_8601_datetime_with_milliseconds(datetime.now())
        self.state_machine_arn = state_machine_arn
        self.execution_input = execution_input
        self.status = "RUNNING"
        self.stop_date = None

    def get_execution_history(self, roleArn):
        sf_execution_history_type = settings.get_sf_execution_history_type()
        if sf_execution_history_type == "SUCCESS":
            return [
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzlocal())
                    ),
                    "type": "ExecutionStarted",
                    "id": 1,
                    "previousEventId": 0,
                    "executionStartedEventDetails": {
                        "input": "{}",
                        "inputDetails": {"truncated": False},
                        "roleArn": roleArn,
                    },
                },
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzlocal())
                    ),
                    "type": "PassStateEntered",
                    "id": 2,
                    "previousEventId": 0,
                    "stateEnteredEventDetails": {
                        "name": "A State",
                        "input": "{}",
                        "inputDetails": {"truncated": False},
                    },
                },
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzlocal())
                    ),
                    "type": "PassStateExited",
                    "id": 3,
                    "previousEventId": 2,
                    "stateExitedEventDetails": {
                        "name": "A State",
                        "output": "An output",
                        "outputDetails": {"truncated": False},
                    },
                },
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 20, tzinfo=tzlocal())
                    ),
                    "type": "ExecutionSucceeded",
                    "id": 4,
                    "previousEventId": 3,
                    "executionSucceededEventDetails": {
                        "output": "An output",
                        "outputDetails": {"truncated": False},
                    },
                },
            ]
        elif sf_execution_history_type == "FAILURE":
            return [
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 0, tzinfo=tzlocal())
                    ),
                    "type": "ExecutionStarted",
                    "id": 1,
                    "previousEventId": 0,
                    "executionStartedEventDetails": {
                        "input": "{}",
                        "inputDetails": {"truncated": False},
                        "roleArn": roleArn,
                    },
                },
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzlocal())
                    ),
                    "type": "FailStateEntered",
                    "id": 2,
                    "previousEventId": 0,
                    "stateEnteredEventDetails": {
                        "name": "A State",
                        "input": "{}",
                        "inputDetails": {"truncated": False},
                    },
                },
                {
                    "timestamp": iso_8601_datetime_with_milliseconds(
                        datetime(2020, 1, 1, 0, 0, 10, tzinfo=tzlocal())
                    ),
                    "type": "ExecutionFailed",
                    "id": 3,
                    "previousEventId": 2,
                    "executionFailedEventDetails": {
                        "error": "AnError",
                        "cause": "An error occurred!",
                    },
                },
            ]

    def stop(self):
        self.status = "ABORTED"
        self.stop_date = iso_8601_datetime_with_milliseconds(datetime.now())


class StepFunctionBackend(BaseBackend):

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.create_state_machine
    # A name must not contain:
    # whitespace
    # brackets < > { } [ ]
    # wildcard characters ? *
    # special characters " # % \ ^ | ~ ` $ & , ; : /
    invalid_chars_for_name = [
        " ",
        "{",
        "}",
        "[",
        "]",
        "<",
        ">",
        "?",
        "*",
        '"',
        "#",
        "%",
        "\\",
        "^",
        "|",
        "~",
        "`",
        "$",
        "&",
        ",",
        ";",
        ":",
        "/",
    ]
    # control characters (U+0000-001F , U+007F-009F )
    invalid_unicodes_for_name = [
        "\u0000",
        "\u0001",
        "\u0002",
        "\u0003",
        "\u0004",
        "\u0005",
        "\u0006",
        "\u0007",
        "\u0008",
        "\u0009",
        "\u000A",
        "\u000B",
        "\u000C",
        "\u000D",
        "\u000E",
        "\u000F",
        "\u0010",
        "\u0011",
        "\u0012",
        "\u0013",
        "\u0014",
        "\u0015",
        "\u0016",
        "\u0017",
        "\u0018",
        "\u0019",
        "\u001A",
        "\u001B",
        "\u001C",
        "\u001D",
        "\u001E",
        "\u001F",
        "\u007F",
        "\u0080",
        "\u0081",
        "\u0082",
        "\u0083",
        "\u0084",
        "\u0085",
        "\u0086",
        "\u0087",
        "\u0088",
        "\u0089",
        "\u008A",
        "\u008B",
        "\u008C",
        "\u008D",
        "\u008E",
        "\u008F",
        "\u0090",
        "\u0091",
        "\u0092",
        "\u0093",
        "\u0094",
        "\u0095",
        "\u0096",
        "\u0097",
        "\u0098",
        "\u0099",
        "\u009A",
        "\u009B",
        "\u009C",
        "\u009D",
        "\u009E",
        "\u009F",
    ]
    accepted_role_arn_format = re.compile(
        "arn:aws:iam::(?P<account_id>[0-9]{12}):role/.+"
    )
    accepted_mchn_arn_format = re.compile(
        "arn:aws:states:[-0-9a-zA-Z]+:(?P<account_id>[0-9]{12}):stateMachine:.+"
    )
    accepted_exec_arn_format = re.compile(
        "arn:aws:states:[-0-9a-zA-Z]+:(?P<account_id>[0-9]{12}):execution:.+"
    )

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.state_machines = []
        self.executions = []
        self._account_id = None

    def create_state_machine(self, name, definition, roleArn, tags=None):
        self._validate_name(name)
        self._validate_role_arn(roleArn)
        arn = f"arn:aws:states:{self.region_name}:{self.account_id}:stateMachine:{name}"
        try:
            return self.describe_state_machine(arn)
        except StateMachineDoesNotExist:
            state_machine = StateMachine(arn, name, definition, roleArn, tags)
            self.state_machines.append(state_machine)
            return state_machine

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_state_machines(self):
        state_machines = sorted(self.state_machines, key=lambda x: x.creation_date)
        return state_machines

    def describe_state_machine(self, arn):
        self._validate_machine_arn(arn)
        sm = next((x for x in self.state_machines if x.arn == arn), None)
        if not sm:
            raise StateMachineDoesNotExist(
                "State Machine Does Not Exist: '" + arn + "'"
            )
        return sm

    def delete_state_machine(self, arn):
        self._validate_machine_arn(arn)
        sm = next((x for x in self.state_machines if x.arn == arn), None)
        if sm:
            self.state_machines.remove(sm)

    def update_state_machine(self, arn, definition=None, role_arn=None):
        sm = self.describe_state_machine(arn)
        updates = {
            "definition": definition,
            "roleArn": role_arn,
        }
        sm.update(**updates)
        return sm

    def start_execution(self, state_machine_arn, name=None, execution_input=None):
        state_machine = self.describe_state_machine(state_machine_arn)
        execution = state_machine.start_execution(
            region_name=self.region_name,
            account_id=self.account_id,
            execution_name=name or str(uuid4()),
            execution_input=execution_input,
        )
        return execution

    def stop_execution(self, execution_arn):
        self._validate_execution_arn(execution_arn)
        state_machine = self._get_state_machine_for_execution(execution_arn)
        return state_machine.stop_execution(execution_arn)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_executions(self, state_machine_arn, status_filter=None):
        executions = self.describe_state_machine(state_machine_arn).executions

        if status_filter:
            executions = list(filter(lambda e: e.status == status_filter, executions))

        executions = sorted(executions, key=lambda x: x.start_date, reverse=True)
        return executions

    def describe_execution(self, execution_arn):
        self._validate_execution_arn(execution_arn)
        state_machine = self._get_state_machine_for_execution(execution_arn)
        exctn = next(
            (x for x in state_machine.executions if x.execution_arn == execution_arn),
            None,
        )
        if not exctn:
            raise ExecutionDoesNotExist(
                "Execution Does Not Exist: '" + execution_arn + "'"
            )
        return exctn

    def get_execution_history(self, execution_arn):
        self._validate_execution_arn(execution_arn)
        state_machine = self._get_state_machine_for_execution(execution_arn)
        execution = next(
            (x for x in state_machine.executions if x.execution_arn == execution_arn),
            None,
        )
        if not execution:
            raise ExecutionDoesNotExist(
                "Execution Does Not Exist: '" + execution_arn + "'"
            )
        return execution.get_execution_history(state_machine.roleArn)

    def list_tags_for_resource(self, arn):
        try:
            state_machine = self.describe_state_machine(arn)
            return state_machine.tags or []
        except StateMachineDoesNotExist:
            return []

    def tag_resource(self, resource_arn, tags):
        try:
            state_machine = self.describe_state_machine(resource_arn)
            state_machine.add_tags(tags)
        except StateMachineDoesNotExist:
            raise ResourceNotFound(resource_arn)

    def untag_resource(self, resource_arn, tag_keys):
        try:
            state_machine = self.describe_state_machine(resource_arn)
            state_machine.remove_tags(tag_keys)
        except StateMachineDoesNotExist:
            raise ResourceNotFound(resource_arn)

    def _validate_name(self, name):
        if any(invalid_char in name for invalid_char in self.invalid_chars_for_name):
            raise InvalidName("Invalid Name: '" + name + "'")

        if any(name.find(char) >= 0 for char in self.invalid_unicodes_for_name):
            raise InvalidName("Invalid Name: '" + name + "'")

    def _validate_role_arn(self, role_arn):
        self._validate_arn(
            arn=role_arn,
            regex=self.accepted_role_arn_format,
            invalid_msg="Invalid Role Arn: '" + role_arn + "'",
        )

    def _validate_machine_arn(self, machine_arn):
        self._validate_arn(
            arn=machine_arn,
            regex=self.accepted_mchn_arn_format,
            invalid_msg="Invalid State Machine Arn: '" + machine_arn + "'",
        )

    def _validate_execution_arn(self, execution_arn):
        self._validate_arn(
            arn=execution_arn,
            regex=self.accepted_exec_arn_format,
            invalid_msg="Execution Does Not Exist: '" + execution_arn + "'",
        )

    def _validate_arn(self, arn, regex, invalid_msg):
        match = regex.match(arn)
        if not arn or not match:
            raise InvalidArn(invalid_msg)

    def _get_state_machine_for_execution(self, execution_arn):
        state_machine_name = execution_arn.split(":")[6]
        state_machine_arn = next(
            (x.arn for x in self.state_machines if x.name == state_machine_name), None
        )
        if not state_machine_arn:
            # Assume that if the state machine arn is not present, then neither will the
            # execution
            raise ExecutionDoesNotExist(
                "Execution Does Not Exist: '" + execution_arn + "'"
            )
        return self.describe_state_machine(state_machine_arn)


stepfunction_backends = BackendDict(StepFunctionBackend, "stepfunctions")
