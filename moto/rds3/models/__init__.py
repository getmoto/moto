from __future__ import unicode_literals

from moto.rds3.utils import create_backends
from .db_cluster import DBCluster  # noqa: F401
from .db_cluster import DBClusterBackend
from .db_cluster_parameter_group import DBClusterParameterGroup  # noqa: F401
from .db_cluster_parameter_group import DBClusterParameterGroupBackend
from .db_cluster_snapshot import DBClusterSnapshot  # noqa: F401
from .db_cluster_snapshot import DBClusterSnapshotBackend
from .db_instance import DBInstance  # noqa: F401
from .db_instance import DBInstanceBackend
from .db_parameter_group import DBParameterGroup  # noqa: F401
from .db_parameter_group import DBParameterGroupBackend
from .db_security_group import DBSecurityGroup  # noqa: F401
from .db_security_group import DBSecurityGroupBackend
from .db_snapshot import DBSnapshot  # noqa: F401
from .db_snapshot import DBSnapshotBackend
from .db_subnet_group import DBSubnetGroup  # noqa: F401
from .db_subnet_group import DBSubnetGroupBackend
from .event import Event  # noqa: F401
from .event import EventBackend
from .log import DBLogFile  # noqa: F401
from .log import LogBackend
from .option_group import OptionGroup  # noqa: F401
from .option_group import OptionGroupBackend
from .tag import TagBackend


class RDS3Backend(
    DBClusterBackend,
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
    TagBackend,
):
    def __init__(self, region):
        super(RDS3Backend, self).__init__()
        self.region = region
        # Create RDS Alias
        rds_key = self.kms.create_key(
            policy="",
            key_usage="ENCRYPT_DECRYPT",
            customer_master_key_spec=None,
            description="Default master key that protects my RDS database volumes when no other key is defined",
            tags=None,
            region=self.region,
        )
        self.kms.add_alias(rds_key.id, "alias/aws/rds")

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)


rds3_backends = create_backends("rds", RDS3Backend)
