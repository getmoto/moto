from __future__ import unicode_literals


class RDSError(Exception):

    fmt = 'An unspecified RDS error occurred.'

    http_status_code = 400

    sender_fault = True

    code = None

    def __init__(self, **kwargs):
        msg = self.fmt.format(**kwargs)
        super(RDSError, self).__init__(msg)
        if self.code is None:
            self.code = self.__class__.__name__


# Exception Classes for not found faults need to be the AWS error code, e.g. DBInstanceNotFound
class ResourceNotFound(RDSError):

    fmt = '{resource_type} {resource_id} not found.'

    http_status_code = 404

    def __init__(self, resource_id):
        resource_type = self.__class__.__name__.replace('NotFound', '')
        super(ResourceNotFound, self).__init__(resource_id=resource_id, resource_type=resource_type)
        # self.code = self.__class__.__name__ + "Fault"


class DBInstanceNotFound(ResourceNotFound):
    pass


class DBClusterNotFound(ResourceNotFound):
    pass


class DBSnapshotNotFound(ResourceNotFound):
    pass


class DBClusterSnapshotNotFound(ResourceNotFound):

    code = "DBClusterSnapshotNotFoundFault"


class DBSecurityGroupNotFound(ResourceNotFound):
    pass


class DBSubnetGroupNotFound(ResourceNotFound):
    pass


class DBParameterGroupNotFound(ResourceNotFound):

    fmt = '{resource_type} not found: {resource_id}'


class DBClusterParameterGroupNotFound(ResourceNotFound):
    pass


class OptionGroupNotFound(ResourceNotFound):
    pass


# Exception Classes for already exists faults need to be the AWS error code, e.g. DBInstanceAlreadyExists
class ResourceAlreadyExists(RDSError):

    fmt = '{resource_type} {resource_id} already exists.'

    http_status_code = 404

    def __init__(self, resource_id):
        resource_type = self.__class__.__name__.replace('AlreadyExists', '')
        super(ResourceAlreadyExists, self).__init__(resource_id=resource_id, resource_type=resource_type)


class DBInstanceAlreadyExists(ResourceAlreadyExists):

    fmt = 'DB Instance already exists.'


class DBParameterGroupAlreadyExists(ResourceAlreadyExists):

    fmt = 'Parameter group {resource_id} already exists'


class DBClusterParameterGroupAlreadyExists(ResourceAlreadyExists):

    fmt = 'Parameter group {resource_id} already exists'


class OptionGroupAlreadyExists(ResourceAlreadyExists):

    fmt = 'Option group {resource_id} already exists'


class DBClusterSnapshotAlreadyExists(ResourceAlreadyExists):

    fmt = 'DB Cluster Snapshot already exists'


class DBSnapshotAlreadyExists(ResourceAlreadyExists):

    fmt = 'Cannot create the snapshot because a snapshot with the identifier {resource_id} already exists.'


class InvalidDBClusterStateFault(RDSError):

    fmt = ('Invalid DB type, when trying to perform StopDBInstance on {resource_id}. '
           'See AWS RDS documentation on rds.stop_db_instance')

    def __init__(self, database_identifier):
        super(InvalidDBClusterStateFault, self).__init__(resource_id=database_identifier)


class DBClusterToBeDeletedHasActiveMembers(RDSError):

    fmt = 'Cluster cannot be deleted, it still contains DB instances in non-deleting state.'


class InvalidDBInstanceState(RDSError):

    fmt = 'Instance {resource_id} is not {status_msg}.'

    def __init__(self, database_identifier, istate):
        estate = "in available state" if istate == 'stop' else "stopped, it cannot be started"
        super(InvalidDBInstanceState, self).__init__(resource_id=database_identifier, status_msg=estate)


class SnapshotQuotaExceeded(RDSError):

    fmt = 'The request cannot be processed because it would exceed the maximum number of snapshots.'


class InvalidParameterValue(RDSError):

    code = 'InvalidParameterValue'

    fmt = '{error_message}'

    def __init__(self, error_message=None, **kwargs):
        if error_message:
            kwargs['error_message'] = error_message
        super(InvalidParameterValue, self).__init__(**kwargs)


class InvalidParameterCombination(RDSError):

    code = 'InvalidParameterCombination'

    fmt = '{error_message}'

    def __init__(self, error_message=None, **kwargs):
        if error_message:
            kwargs['error_message'] = error_message
        super(InvalidParameterCombination, self).__init__(**kwargs)


class InvalidAvailabilityZones(RDSError):

    code = 'InvalidVPCNetworkStateFault'

    fmt = ('Availability zone{zone_plural} \'[{invalid_zones}]\' '
           '{verb} unavailable in this region, please choose another zone set.')

    def __init__(self, invalid_zones):
        kwargs = {
            'zone_plural': 's' if len(invalid_zones) > 1 else '',
            'invalid_zones': ', '.join(sorted(list(invalid_zones))),
            'verb': 'are' if len(invalid_zones) > 1 else 'is'
        }
        super(InvalidAvailabilityZones, self).__init__(**kwargs)


class InvalidDBSnapshotIdentifierValue(InvalidParameterValue):

    fmt = ('{resource_id} is not a valid identifier. Identifiers '
           'must begin with a letter; must contain only ASCII letters, '
           'digits, and hyphens; and must not end with a hyphen or '
           'contain two consecutive hyphens.')

    def __init__(self, identifier):
        super(InvalidDBSnapshotIdentifierValue, self).__init__(resource_id=identifier)
