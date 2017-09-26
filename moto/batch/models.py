from __future__ import unicode_literals
import boto3
import re
from moto.core import BaseBackend, BaseModel
from moto.iam import iam_backends
from moto.ec2 import ec2_backends

from .exceptions import InvalidParameterValueException, InternalFailure
from .utils import make_arn_for_compute_env
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.iam.exceptions import IAMNotFoundException


DEFAULT_ACCOUNT_ID = 123456789012
COMPUTE_ENVIRONMENT_NAME_REGEX = re.compile(r'^[A-Za-z0-9_]{1,128}$')


class ComputeEnvironment(BaseModel):
    def __init__(self, compute_environment_name, _type, state, compute_resources, service_role, region_name):
        self.compute_environment_name = compute_environment_name
        self.type = _type
        self.state = state
        self.compute_resources = compute_resources
        self.service_role = service_role
        self.arn = make_arn_for_compute_env(DEFAULT_ACCOUNT_ID, compute_environment_name, region_name)


class BatchBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(BatchBackend, self).__init__()
        self.region_name = region_name

        self._compute_environments = {}

    @property
    def iam_backend(self):
        """
        :return: IAM Backend
        :rtype: moto.iam.models.IAMBackend
        """
        return iam_backends['global']

    @property
    def ec2_backend(self):
        """
        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.region_name]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def get_compute_environment(self, arn):
        return self._compute_environments.get(arn)

    def get_compute_environment_by_name(self, name):
        for comp_env in self._compute_environments.values():
            if comp_env.name == name:
                return comp_env
        return None

    def create_compute_environment(self, compute_environment_name, _type, state, compute_resources, service_role):
        # Validate
        if COMPUTE_ENVIRONMENT_NAME_REGEX.match(compute_environment_name) is None:
            raise InvalidParameterValueException('Compute environment name does not match ^[A-Za-z0-9_]{1,128}$')

        if self.get_compute_environment_by_name(compute_environment_name) is not None:
            raise InvalidParameterValueException('A compute environment already exists with the name {0}'.format(compute_environment_name))

        # Look for IAM role
        try:
            self.iam_backend.get_role_by_arn(service_role)
        except IAMNotFoundException:
            raise InvalidParameterValueException('Could not find IAM role {0}'.format(service_role))

        if _type not in ('MANAGED', 'UNMANAGED'):
            raise InvalidParameterValueException('type {0} must be one of MANAGED | UNMANAGED'.format(service_role))

        if state is not None and state not in ('ENABLED', 'DISABLED'):
            raise InvalidParameterValueException('state {0} must be one of ENABLED | DISABLED'.format(state))

        if compute_resources is None and _type == 'MANAGED':
            raise InvalidParameterValueException('computeResources must be specified when creating a MANAGED environment'.format(state))
        elif compute_resources is not None:
            self._validate_compute_resources(compute_resources)

        # By here, all values except SPOT ones have been validated
        new_comp_env = ComputeEnvironment(
            compute_environment_name, _type, state,
            compute_resources, service_role,
            region_name=self.region_name
        )
        self._compute_environments[new_comp_env.arn] = new_comp_env

        # TODO scale out if MANAGED and we have compute instance types

        return compute_environment_name, new_comp_env.arn

    def _validate_compute_resources(self, cr):
        if 'instanceRole' not in cr:
            raise InvalidParameterValueException('computeResources must contain instanceRole')
        elif self.iam_backend.get_role_by_arn(cr['instanceRole']) is None:
            raise InvalidParameterValueException('could not find instanceRole {0}'.format(cr['instanceRole']))

        # TODO move the not in checks to a loop, or create a json schema validator class
        if 'maxvCpus' not in cr:
            raise InvalidParameterValueException('computeResources must contain maxVCpus')
        if 'minvCpus' not in cr:
            raise InvalidParameterValueException('computeResources must contain minVCpus')
        if cr['maxvCpus'] < 0:
            raise InvalidParameterValueException('maxVCpus must be positive')
        if cr['minvCpus'] < 0:
            raise InvalidParameterValueException('minVCpus must be positive')
        if cr['maxvCpus'] < cr['minvCpus']:
            raise InvalidParameterValueException('maxVCpus must be greater than minvCpus')

        # TODO check instance types when that logic exists
        if 'instanceTypes' not in cr:
            raise InvalidParameterValueException('computeResources must contain instanceTypes')
        if len(cr['instanceTypes']) == 0:
            raise InvalidParameterValueException('At least 1 instance type must be provided')

        if 'securityGroupIds' not in cr:
            raise InvalidParameterValueException('computeResources must contain securityGroupIds')
        for sec_id in cr['securityGroupIds']:
            if self.ec2_backend.get_security_group_from_id(sec_id) is None:
                raise InvalidParameterValueException('security group {0} does not exist'.format(sec_id))
        if len(cr['securityGroupIds']) == 0:
            raise InvalidParameterValueException('At least 1 security group must be provided')

        if 'subnets' not in cr:
            raise InvalidParameterValueException('computeResources must contain subnets')
        for subnet_id in cr['subnets']:
            try:
                self.ec2_backend.get_subnet(subnet_id)
            except InvalidSubnetIdError:
                raise InvalidParameterValueException('subnet {0} does not exist'.format(subnet_id))
        if len(cr['subnets']) == 0:
            raise InvalidParameterValueException('At least 1 subnet must be provided')

        if 'type' not in cr:
            raise InvalidParameterValueException('computeResources must contain type')
        if cr['type'] not in ('EC2', 'SPOT'):
            raise InvalidParameterValueException('computeResources.type must be either EC2 | SPOT')

        if cr['type'] == 'SPOT':
            raise InternalFailure('SPOT NOT SUPPORTED YET')


available_regions = boto3.session.Session().get_available_regions("batch")
batch_backends = {region: BatchBackend(region_name=region) for region in available_regions}
