import re
from datetime import datetime

from boto3 import Session

from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.sts.models import ACCOUNT_ID
from uuid import uuid4
from .exceptions import (
    ExecutionDoesNotExist,
    InvalidArn,
    InvalidName,
    StateMachineDoesNotExist,
)


class StateMachine:
    def __init__(self, arn, name, definition, roleArn, tags=None):
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.arn = arn
        self.name = name
        self.definition = definition
        self.roleArn = roleArn
        self.tags = tags


class Execution:
    def __init__(
        self,
        region_name,
        account_id,
        state_machine_name,
        execution_name,
        state_machine_arn,
    ):
        execution_arn = "arn:aws:states:{}:{}:execution:{}:{}"
        execution_arn = execution_arn.format(
            region_name, account_id, state_machine_name, execution_name
        )
        self.execution_arn = execution_arn
        self.name = execution_name
        self.start_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.state_machine_arn = state_machine_arn
        self.status = "RUNNING"
        self.stop_date = None

    def stop(self):
        self.status = "ABORTED"
        self.stop_date = iso_8601_datetime_without_milliseconds(datetime.now())


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
        u"\u0000",
        u"\u0001",
        u"\u0002",
        u"\u0003",
        u"\u0004",
        u"\u0005",
        u"\u0006",
        u"\u0007",
        u"\u0008",
        u"\u0009",
        u"\u000A",
        u"\u000B",
        u"\u000C",
        u"\u000D",
        u"\u000E",
        u"\u000F",
        u"\u0010",
        u"\u0011",
        u"\u0012",
        u"\u0013",
        u"\u0014",
        u"\u0015",
        u"\u0016",
        u"\u0017",
        u"\u0018",
        u"\u0019",
        u"\u001A",
        u"\u001B",
        u"\u001C",
        u"\u001D",
        u"\u001E",
        u"\u001F",
        u"\u007F",
        u"\u0080",
        u"\u0081",
        u"\u0082",
        u"\u0083",
        u"\u0084",
        u"\u0085",
        u"\u0086",
        u"\u0087",
        u"\u0088",
        u"\u0089",
        u"\u008A",
        u"\u008B",
        u"\u008C",
        u"\u008D",
        u"\u008E",
        u"\u008F",
        u"\u0090",
        u"\u0091",
        u"\u0092",
        u"\u0093",
        u"\u0094",
        u"\u0095",
        u"\u0096",
        u"\u0097",
        u"\u0098",
        u"\u0099",
        u"\u009A",
        u"\u009B",
        u"\u009C",
        u"\u009D",
        u"\u009E",
        u"\u009F",
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

    def __init__(self, region_name):
        self.state_machines = []
        self.executions = []
        self.region_name = region_name
        self._account_id = None

    def create_state_machine(self, name, definition, roleArn, tags=None):
        self._validate_name(name)
        self._validate_role_arn(roleArn)
        arn = (
            "arn:aws:states:"
            + self.region_name
            + ":"
            + str(self._get_account_id())
            + ":stateMachine:"
            + name
        )
        try:
            return self.describe_state_machine(arn)
        except StateMachineDoesNotExist:
            state_machine = StateMachine(arn, name, definition, roleArn, tags)
            self.state_machines.append(state_machine)
            return state_machine

    def list_state_machines(self):
        return self.state_machines

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

    def start_execution(self, state_machine_arn, name=None):
        state_machine_name = self.describe_state_machine(state_machine_arn).name
        execution = Execution(
            region_name=self.region_name,
            account_id=self._get_account_id(),
            state_machine_name=state_machine_name,
            execution_name=name or str(uuid4()),
            state_machine_arn=state_machine_arn,
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

    def list_executions(self, state_machine_arn):
        return [
            execution
            for execution in self.executions
            if execution.state_machine_arn == state_machine_arn
        ]

    def describe_execution(self, arn):
        self._validate_execution_arn(arn)
        exctn = next((x for x in self.executions if x.execution_arn == arn), None)
        if not exctn:
            raise ExecutionDoesNotExist("Execution Does Not Exist: '" + arn + "'")
        return exctn

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

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

    def _get_account_id(self):
        return ACCOUNT_ID


stepfunction_backends = {}
for region in Session().get_available_regions("stepfunctions"):
    stepfunction_backends[region] = StepFunctionBackend(region)
for region in Session().get_available_regions(
    "stepfunctions", partition_name="aws-us-gov"
):
    stepfunction_backends[region] = StepFunctionBackend(region)
for region in Session().get_available_regions("stepfunctions", partition_name="aws-cn"):
    stepfunction_backends[region] = StepFunctionBackend(region)
