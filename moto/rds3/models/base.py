from __future__ import unicode_literals

import datetime

from moto.core import BaseBackend, BaseModel
from moto.core.utils import iso_8601_datetime_with_milliseconds
from moto.ec2 import ec2_backends
from moto.iam import iam_backends
from moto.kms import kms_backends


ACCOUNT_ID = 1234567890


class BaseRDSModel(BaseModel):

    resource_type = None

    def __init__(self, backend):
        self.backend = backend
        self.created = iso_8601_datetime_with_milliseconds(datetime.datetime.now())

    @property
    def resource_id(self):
        raise NotImplementedError("Subclasses must implement resource_id property.")

    @property
    def region(self):
        return self.backend.region

    @property
    def arn(self):
        return "arn:aws:rds:{region}:{account_id}:{resource_type}:{resource_id}".format(
            region=self.backend.region,
            account_id=ACCOUNT_ID,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
        )

    @staticmethod
    def get_regional_backend(region):
        from . import rds3_backends

        return rds3_backends[region]

    @staticmethod
    def get_regional_ec2_backend(region):
        from moto.ec2.models import ec2_backends

        return ec2_backends[region]


class BaseRDSBackend(BaseBackend):

    region = None

    @property
    def ec2(self):
        """
        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.region]

    @property
    def iam(self):
        """
        :return: IAM Backend
        :rtype: moto.iam.models.IAMBackend
        """
        return iam_backends["global"]

    @property
    def kms(self):
        """
        :return: KMS Backend
        :rtype: moto.kms.models.KMSBackend
        """
        from moto.kms.models import KmsBackend

        if self.region not in kms_backends:
            kms_backends[self.region] = KmsBackend()
        return kms_backends[self.region]

    @staticmethod
    def get_regional_backend(region):
        """
        :return: RDS Backend
        :rtype: moto.rds3.models.RDS3Backend
        """
        from . import rds3_backends

        return rds3_backends[region]

    # Basic interface, mainly to avoid unresolved ref errors from PyCharm
    def describe_db_instances(self, db_instance_identifier=None):
        pass  # pragma: no cover

    def get_db_cluster(self, db_cluster_identifier):
        pass  # pragma: no cover

    def get_db_instance(self, db_instance_identifier):
        pass  # pragma: no cover

    def get_db_snapshot(self, db_snapshot_identifier):
        pass  # pragma: no cover

    def create_db_snapshot(
        self,
        db_instance_identifier,
        db_snapshot_identifier,
        tags=None,
        snapshot_type="manual",
    ):
        pass  # pragma: no cover

    def delete_db_snapshot(self, db_snapshot_identifier):
        pass  # pragma: no cover

    def describe_db_snapshots(
        self,
        db_instance_identifier=None,
        db_snapshot_identifier=None,
        snapshot_type=None,
    ):
        pass  # pragma: no cover

    def get_db_subnet_group(self, subnet_group_name):
        pass  # pragma: no cover

    def get_option_group(self, option_group_name):
        pass  # pragma: no cover

    def get_db_parameter_group(self, db_parameter_group_name):
        pass  # pragma: no cover

    def get_db_cluster_parameter_group(self, db_cluster_parameter_group_name):
        pass  # pragma: no cover

    def get_db_cluster_snapshot(self, db_cluster_snapshot_identifier):
        pass  # pragma: no cover

    def create_db_cluster_snapshot(
        self, db_cluster_identifier, db_cluster_snapshot_identifier, tags, snapshot_type
    ):
        pass  # pragma: no cover
