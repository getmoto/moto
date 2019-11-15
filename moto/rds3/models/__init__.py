from __future__ import unicode_literals

import boto3

from moto.core import utils
from moto.core.responses import method_names_from_class
from .db_cluster import DBCluster                                   # noqa: F401
from .db_cluster import DBClusterBackend
from .db_cluster_parameter_group import DBClusterParameterGroup     # noqa: F401
from .db_cluster_parameter_group import DBClusterParameterGroupBackend
from .db_cluster_snapshot import DBClusterSnapshot                  # noqa: F401
from .db_cluster_snapshot import DBClusterSnapshotBackend
from .db_instance import DBInstance                                 # noqa: F401
from .db_instance import DBInstanceBackend
from .db_parameter_group import DBParameterGroup                    # noqa: F401
from .db_parameter_group import DBParameterGroupBackend
from .db_security_group import DBSecurityGroup                      # noqa: F401
from .db_security_group import DBSecurityGroupBackend
from .db_snapshot import DBSnapshot                                 # noqa: F401
from .db_snapshot import DBSnapshotBackend
from .db_subnet_group import DBSubnetGroup                          # noqa: F401
from .db_subnet_group import DBSubnetGroupBackend
from .event import Event                                            # noqa: F401
from .event import EventBackend
from .log import DBLogFile                                          # noqa: F401
from .log import LogBackend
from .option_group import OptionGroup                               # noqa: F401
from .option_group import OptionGroupBackend
from .tag import TagBackend


class RDS3Backend(DBClusterBackend,
                  DBClusterParameterGroupBackend,
                  DBClusterSnapshotBackend,
                  DBInstanceBackend,
                  DBParameterGroupBackend,
                  DBSecurityGroupBackend,
                  DBSnapshotBackend,
                  DBSubnetGroupBackend,
                  EventBackend,
                  LogBackend,
                  OptionGroupBackend,
                  TagBackend):

    def __init__(self, region):
        super(RDS3Backend, self).__init__()
        self.region = region
        # Create RDS Alias
        rds_key = self.kms.create_key(
            policy='',
            key_usage='ENCRYPT_DECRYPT',
            description='Default master key that protects my RDS database volumes when no other key is defined',
            tags=None,
            region=self.region)
        self.kms.add_alias(rds_key.id, 'alias/aws/rds')

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    @classmethod
    def methods_implemented(cls):
        client = boto3.client('rds', region_name='us-east-1')
        aws_methods = [utils.camelcase_to_underscores(method) for method in client.meta.service_model.operation_names]
        backend_methods = method_names_from_class(cls('us-east-1'))  # region doesn't matter here
        return set(backend_methods).intersection(set(aws_methods))


available_regions = boto3.session.Session().get_available_regions('rds')
rds3_backends = {region: RDS3Backend(region) for region in available_regions}
