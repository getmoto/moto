import boto
import boto3
import re
from datetime import datetime
from moto.core import BaseBackend
from moto.core.utils import iso_8601_datetime_without_milliseconds
from .exceptions import AccessDeniedException, InvalidArn, InvalidName, StateMachineDoesNotExist


class StateMachine():
    def __init__(self, arn, name, definition, roleArn, tags=None):
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.arn = arn
        self.name = name
        self.definition = definition
        self.roleArn = roleArn
        self.tags = tags


class StepFunctionBackend(BaseBackend):

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/stepfunctions.html#SFN.Client.create_state_machine
    # A name must not contain:
    # whitespace
    # brackets < > { } [ ]
    # wildcard characters ? *
    # special characters " # % \ ^ | ~ ` $ & , ; : /
    invalid_chars_for_name = [' ', '{', '}', '[', ']', '<', '>',
                              '?', '*',
                              '"', '#', '%', '\\', '^', '|', '~', '`', '$', '&', ',', ';', ':', '/']
    # control characters (U+0000-001F , U+007F-009F )
    invalid_unicodes_for_name = [u'\u0000', u'\u0001', u'\u0002', u'\u0003', u'\u0004',
                                 u'\u0005', u'\u0006', u'\u0007', u'\u0008', u'\u0009',
                                 u'\u000A', u'\u000B', u'\u000C', u'\u000D', u'\u000E', u'\u000F',
                                 u'\u0010', u'\u0011', u'\u0012', u'\u0013', u'\u0014',
                                 u'\u0015', u'\u0016', u'\u0017', u'\u0018', u'\u0019',
                                 u'\u001A', u'\u001B', u'\u001C', u'\u001D', u'\u001E', u'\u001F',
                                 u'\u007F',
                                 u'\u0080', u'\u0081', u'\u0082', u'\u0083', u'\u0084', u'\u0085',
                                 u'\u0086', u'\u0087', u'\u0088', u'\u0089',
                                 u'\u008A', u'\u008B', u'\u008C', u'\u008D', u'\u008E', u'\u008F',
                                 u'\u0090', u'\u0091', u'\u0092', u'\u0093', u'\u0094', u'\u0095',
                                 u'\u0096', u'\u0097', u'\u0098', u'\u0099',
                                 u'\u009A', u'\u009B', u'\u009C', u'\u009D', u'\u009E', u'\u009F']
    accepted_role_arn_format = re.compile('arn:aws:iam:(?P<account_id>[0-9]{12}):role/.+')
    accepted_mchn_arn_format = re.compile('arn:aws:states:[-0-9a-zA-Z]+:(?P<account_id>[0-9]{12}):stateMachine:.+')

    def __init__(self, region_name):
        self.state_machines = []
        self.region_name = region_name
        self._account_id = None

    def create_state_machine(self, name, definition, roleArn, tags=None):
        self._validate_name(name)
        self._validate_role_arn(roleArn)
        arn = 'arn:aws:states:' + self.region_name + ':' + str(self._get_account_id()) + ':stateMachine:' + name
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
            raise StateMachineDoesNotExist("State Machine Does Not Exist: '" + arn + "'")
        return sm

    def delete_state_machine(self, arn):
        self._validate_machine_arn(arn)
        sm = next((x for x in self.state_machines if x.arn == arn), None)
        if sm:
            self.state_machines.remove(sm)

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
        self._validate_arn(arn=role_arn,
                           regex=self.accepted_role_arn_format,
                           invalid_msg="Invalid Role Arn: '" + role_arn + "'",
                           access_denied_msg='Cross-account pass role is not allowed.')

    def _validate_machine_arn(self, machine_arn):
        self._validate_arn(arn=machine_arn,
                           regex=self.accepted_mchn_arn_format,
                           invalid_msg="Invalid Role Arn: '" + machine_arn + "'",
                           access_denied_msg='User moto is not authorized to access this resource')

    def _validate_arn(self, arn, regex, invalid_msg, access_denied_msg):
        match = regex.match(arn)
        if not arn or not match:
            raise InvalidArn(invalid_msg)

        if self._get_account_id() != match.group('account_id'):
            raise AccessDeniedException(access_denied_msg)

    def _get_account_id(self):
        if self._account_id:
            return self._account_id
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        self._account_id = identity['Account']
        return self._account_id


stepfunction_backends = {_region.name: StepFunctionBackend(_region.name) for _region in boto.awslambda.regions()}
