from __future__ import unicode_literals

from werkzeug.exceptions import HTTPException

from moto.core.utils import get_random_message_id


class RDSClientError(HTTPException):

    code = 400

    def __init__(self, code, message):
        super(RDSClientError, self).__init__()
        self.error_code = code
        self.error_message = message
        self.description = self.to_dict()

    def to_dict(self):
        return {
            'RDSClientError': {
                'Error': {
                    'Code': self.error_code,
                    'Message': self.error_message,
                    'Type': 'Sender'
                },
                'RequestId': get_random_message_id()
            }
        }


class DBClusterNotFound(RDSClientError):

    code = 404

    def __init__(self, db_cluster_identifier):
        super(DBClusterNotFound, self).__init__(
            'DBClusterNotFound',
            "DBCluster {0} not found.".format(db_cluster_identifier))


class DBInstanceNotFound(RDSClientError):

    code = 404

    def __init__(self, database_identifier):
        super(DBInstanceNotFound, self).__init__(
            'DBInstanceNotFound',
            "Database {0} not found.".format(database_identifier))


class DBInstanceAlreadyExists(RDSClientError):

    def __init__(self):
        super(DBInstanceAlreadyExists, self).__init__(
            'DBInstanceAlreadyExists',
            'DB Instance already exists')


class DBParameterGroupAlreadyExists(RDSClientError):

    def __init__(self, db_parameter_group_name):
        super(DBParameterGroupAlreadyExists, self).__init__(
            'DBParameterAlreadyExists',
            'Parameter group {} already exists'.format(db_parameter_group_name))


class DBClusterParameterGroupAlreadyExists(RDSClientError):

    def __init__(self, db_cluster_parameter_group_name):
        super(DBClusterParameterGroupAlreadyExists, self).__init__(
            'DBClusterParameterAlreadyExists',
            'Parameter group {} already exists'.format(db_cluster_parameter_group_name))


class OptionGroupAlreadyExists(RDSClientError):

    def __init__(self, option_group_name):
        super(OptionGroupAlreadyExists, self).__init__(
            'OptionGroupAlreadyExists',
            'Option group {} already exists'.format(option_group_name))


class DBClusterSnapshotAlreadyExists(RDSClientError):
    def __init__(self):
        super(DBClusterSnapshotAlreadyExists, self).__init__(
            'DBClusterSnapshotAlreadyExists',
            'DB Cluster Snapshot already exists')


class DBSnapshotNotFound(RDSClientError):

    code = 404

    def __init__(self, snapshot_identifier):
        super(DBSnapshotNotFound, self).__init__(
            'DBSnapshotNotFound',
            "DBSnapshot {0} not found.".format(snapshot_identifier))


class DBClusterSnapshotNotFound(RDSClientError):
    code = 404

    def __init__(self, snapshot_identifier):
        super(DBClusterSnapshotNotFound, self).__init__(
            'DBClusterSnapshotNotFound',
            "DBClusterSnapshot {0} not found.".format(snapshot_identifier))


class DBSecurityGroupNotFound(RDSClientError):

    code = 404

    def __init__(self, security_group_name):
        super(DBSecurityGroupNotFound, self).__init__(
            'DBSecurityGroupNotFound',
            "Security Group {0} not found.".format(security_group_name))


class DBSubnetGroupNotFound(RDSClientError):

    code = 404

    def __init__(self, subnet_group_name):
        super(DBSubnetGroupNotFound, self).__init__(
            'DBSubnetGroupNotFound',
            "Subnet Group {0} not found.".format(subnet_group_name))


class DBParameterGroupNotFound(RDSClientError):

    code = 404

    def __init__(self, db_parameter_group_name):
        super(DBParameterGroupNotFound, self).__init__(
            'DBParameterGroupNotFound',
            'DBParameterGroup not found: {}'.format(db_parameter_group_name))


class DBClusterParameterGroupNotFound(RDSClientError):

    code = 404

    def __init__(self, db_cluster_parameter_group_name):
        super(DBClusterParameterGroupNotFound, self).__init__(
            'DBParameterGroupNotFound',  # Code is correct.  No 'Cluster' needed.
            'DBClusterParameterGroup not found: {}'.format(db_cluster_parameter_group_name))


class OptionGroupNotFound(RDSClientError):

    code = 404

    def __init__(self, option_group_name):
        super(OptionGroupNotFound, self).__init__(
            'OptionGroupNotFoundFault',
            'Specified OptionGroupName: {} not found.'.format(option_group_name))


class InvalidDBClusterStateFault(RDSClientError):

    def __init__(self, database_identifier):
        super(InvalidDBClusterStateFault, self).__init__(
            'InvalidDBClusterStateFault',
            'Invalid DB type, when trying to perform StopDBInstance on {0}e. '
            'See AWS RDS documentation on rds.stop_db_instance'.format(database_identifier))


class DBClusterToBeDeletedHasActiveMembers(RDSClientError):

    def __init__(self):
        super(DBClusterToBeDeletedHasActiveMembers, self).__init__(
            'InvalidDBClusterStateFault',
            'Cluster cannot be deleted, it still contains DB instances in non-deleting state.')


class InvalidDBInstanceState(RDSClientError):

    def __init__(self, database_identifier, istate):
        estate = "in available state" if istate == 'stop' else "stopped, it cannot be started"
        super(InvalidDBInstanceState, self).__init__(
            'InvalidDBInstanceState',
            'Instance {} is not {}.'.format(database_identifier, estate))


class SnapshotQuotaExceeded(RDSClientError):

    def __init__(self):
        super(SnapshotQuotaExceeded, self).__init__(
            'SnapshotQuotaExceeded',
            'The request cannot be processed because it would exceed the maximum number of snapshots.')


class DBSnapshotAlreadyExists(RDSClientError):

    def __init__(self, database_snapshot_identifier):
        super(DBSnapshotAlreadyExists, self).__init__(
            'DBSnapshotAlreadyExists',
            'Cannot create the snapshot because a snapshot with the '
            'identifier {} already exists.'.format(database_snapshot_identifier))


class InvalidParameterValue(RDSClientError):

    def __init__(self, message):
        super(InvalidParameterValue, self).__init__(
            'InvalidParameterValue',
            message)


class InvalidParameterCombination(RDSClientError):
    def __init__(self, message):
        super(InvalidParameterCombination, self).__init__(
            'InvalidParameterCombination',
            message)


class InvalidAvailabilityZones(RDSClientError):

    def __init__(self, invalid_zones):
        super(InvalidAvailabilityZones, self).__init__(
            'InvalidVPCNetworkStateFault',
            'Availability zone{} \'[{}]\' {} unavailable in this region, '
            'please choose another zone set.'.format(
                's' if len(invalid_zones) > 1 else '',
                ', '.join(sorted(list(invalid_zones))),
                'are' if len(invalid_zones) > 1 else 'is'
            )
        )


class InvalidDBSnapshotIdentifierValue(RDSClientError):

    def __init__(self, identifier):
        super(InvalidDBSnapshotIdentifierValue, self).__init__(
            'InvalidParameterValue',
            '{} is not a valid identifier. Identifiers '
            'must begin with a letter; must contain only ASCII letters, '
            'digits, and hyphens; and must not end with a hyphen or '
            'contain two consecutive hyphens.'.format(identifier))