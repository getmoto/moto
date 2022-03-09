from jinja2 import Template
from werkzeug.exceptions import BadRequest


class RDSClientError(BadRequest):
    def __init__(self, code, message):
        super().__init__()
        template = Template(
            """
        <RDSClientError>
            <Error>
              <Code>{{ code }}</Code>
              <Message>{{ message }}</Message>
              <Type>Sender</Type>
            </Error>
            <RequestId>6876f774-7273-11e4-85dc-39e55ca848d1</RequestId>
        </RDSClientError>"""
        )
        self.description = template.render(code=code, message=message)


class DBInstanceNotFoundError(RDSClientError):
    def __init__(self, database_identifier):
        super().__init__(
            "DBInstanceNotFound",
            "DBInstance {0} not found.".format(database_identifier),
        )


class DBSnapshotNotFoundError(RDSClientError):
    def __init__(self, snapshot_identifier):
        super().__init__(
            "DBSnapshotNotFound", f"DBSnapshot {snapshot_identifier} not found."
        )


class DBSecurityGroupNotFoundError(RDSClientError):
    def __init__(self, security_group_name):
        super().__init__(
            "DBSecurityGroupNotFound",
            f"Security Group {security_group_name} not found.",
        )


class DBSubnetGroupNotFoundError(RDSClientError):
    def __init__(self, subnet_group_name):
        super().__init__(
            "DBSubnetGroupNotFound", f"Subnet Group {subnet_group_name} not found."
        )


class DBParameterGroupNotFoundError(RDSClientError):
    def __init__(self, db_parameter_group_name):
        super().__init__(
            "DBParameterGroupNotFound",
            f"DB Parameter Group {db_parameter_group_name} not found.",
        )


class OptionGroupNotFoundFaultError(RDSClientError):
    def __init__(self, option_group_name):
        super().__init__(
            "OptionGroupNotFoundFault",
            f"Specified OptionGroupName: {option_group_name} not found.",
        )


class InvalidDBClusterStateFaultError(RDSClientError):
    def __init__(self, database_identifier):
        super().__init__(
            "InvalidDBClusterStateFault",
            "Invalid DB type, when trying to perform StopDBInstance on {0}e. See AWS RDS documentation on rds.stop_db_instance".format(
                database_identifier
            ),
        )


class InvalidDBInstanceStateError(RDSClientError):
    def __init__(self, database_identifier, istate):
        estate = (
            "in available state"
            if istate == "stop"
            else "stopped, it cannot be started"
        )
        super().__init__(
            "InvalidDBInstanceState",
            "Instance {} is not {}.".format(database_identifier, estate),
        )


class SnapshotQuotaExceededError(RDSClientError):
    def __init__(self):
        super().__init__(
            "SnapshotQuotaExceeded",
            "The request cannot be processed because it would exceed the maximum number of snapshots.",
        )


class DBSnapshotAlreadyExistsError(RDSClientError):
    def __init__(self, database_snapshot_identifier):
        super().__init__(
            "DBSnapshotAlreadyExists",
            "Cannot create the snapshot because a snapshot with the identifier {} already exists.".format(
                database_snapshot_identifier
            ),
        )


class InvalidParameterValue(RDSClientError):
    def __init__(self, message):
        super().__init__("InvalidParameterValue", message)


class InvalidParameterCombination(RDSClientError):
    def __init__(self, message):
        super().__init__("InvalidParameterCombination", message)


class InvalidDBClusterStateFault(RDSClientError):
    def __init__(self, message):
        super().__init__("InvalidDBClusterStateFault", message)


class DBClusterNotFoundError(RDSClientError):
    def __init__(self, cluster_identifier):
        super().__init__(
            "DBClusterNotFoundFault",
            "DBCluster {} not found.".format(cluster_identifier),
        )


class DBClusterSnapshotNotFoundError(RDSClientError):
    def __init__(self, snapshot_identifier):
        super().__init__(
            "DBClusterSnapshotNotFoundFault",
            "DBClusterSnapshot {} not found.".format(snapshot_identifier),
        )


class DBClusterSnapshotAlreadyExistsError(RDSClientError):
    def __init__(self, database_snapshot_identifier):
        super().__init__(
            "DBClusterSnapshotAlreadyExistsFault",
            "Cannot create the snapshot because a snapshot with the identifier {} already exists.".format(
                database_snapshot_identifier
            ),
        )


class ExportTaskAlreadyExistsError(RDSClientError):
    def __init__(self, export_task_identifier):
        super().__init__(
            "ExportTaskAlreadyExistsFault",
            "Cannot start export task because a task with the identifier {} already exists.".format(
                export_task_identifier
            ),
        )


class ExportTaskNotFoundError(RDSClientError):
    def __init__(self, export_task_identifier):
        super().__init__(
            "ExportTaskNotFoundFault",
            "Cannot cancel export task because a task with the identifier {} is not exist.".format(
                export_task_identifier
            ),
        )


class InvalidExportSourceStateError(RDSClientError):
    def __init__(self, status):
        super().__init__(
            "InvalidExportSourceStateFault",
            "Export source should be 'available' but current status is {}.".format(
                status
            ),
        )


class SubscriptionAlreadyExistError(RDSClientError):
    def __init__(self, subscription_name):
        super().__init__(
            "SubscriptionAlreadyExistFault",
            "Subscription {} already exists.".format(subscription_name),
        )


class SubscriptionNotFoundError(RDSClientError):
    def __init__(self, subscription_name):
        super().__init__(
            "SubscriptionNotFoundFault",
            "Subscription {} not found.".format(subscription_name),
        )
