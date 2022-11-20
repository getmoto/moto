from jinja2 import Template
from moto.core.exceptions import RESTError


class RDSClientError(RESTError):
    def __init__(self, code, message):
        super().__init__(error_type=code, message=message)
        template = Template(
            """
        <ErrorResponse>
            <Error>
              <Code>{{ code }}</Code>
              <Message>{{ message }}</Message>
              <Type>Sender</Type>
            </Error>
            <RequestId>6876f774-7273-11e4-85dc-39e55ca848d1</RequestId>
        </ErrorResponse>"""
        )
        self.description = template.render(code=code, message=message)


class DBInstanceNotFoundError(RDSClientError):
    def __init__(self, database_identifier):
        super().__init__(
            "DBInstanceNotFound", f"DBInstance {database_identifier} not found."
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
            f"Invalid DB type, when trying to perform StopDBInstance on {database_identifier}e. See AWS RDS documentation on rds.stop_db_instance",
        )


class InvalidDBInstanceStateError(RDSClientError):
    def __init__(self, database_identifier, istate):
        estate = (
            "in available state"
            if istate == "stop"
            else "stopped, it cannot be started"
        )
        super().__init__(
            "InvalidDBInstanceState", f"Instance {database_identifier} is not {estate}."
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
            f"Cannot create the snapshot because a snapshot with the identifier {database_snapshot_identifier} already exists.",
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
            "DBClusterNotFoundFault", f"DBCluster {cluster_identifier} not found."
        )


class DBClusterSnapshotNotFoundError(RDSClientError):
    def __init__(self, snapshot_identifier):
        super().__init__(
            "DBClusterSnapshotNotFoundFault",
            f"DBClusterSnapshot {snapshot_identifier} not found.",
        )


class DBClusterSnapshotAlreadyExistsError(RDSClientError):
    def __init__(self, database_snapshot_identifier):
        super().__init__(
            "DBClusterSnapshotAlreadyExistsFault",
            f"Cannot create the snapshot because a snapshot with the identifier {database_snapshot_identifier} already exists.",
        )


class ExportTaskAlreadyExistsError(RDSClientError):
    def __init__(self, export_task_identifier):
        super().__init__(
            "ExportTaskAlreadyExistsFault",
            f"Cannot start export task because a task with the identifier {export_task_identifier} already exists.",
        )


class ExportTaskNotFoundError(RDSClientError):
    def __init__(self, export_task_identifier):
        super().__init__(
            "ExportTaskNotFoundFault",
            f"Cannot cancel export task because a task with the identifier {export_task_identifier} is not exist.",
        )


class InvalidExportSourceStateError(RDSClientError):
    def __init__(self, status):
        super().__init__(
            "InvalidExportSourceStateFault",
            f"Export source should be 'available' but current status is {status}.",
        )


class SubscriptionAlreadyExistError(RDSClientError):
    def __init__(self, subscription_name):
        super().__init__(
            "SubscriptionAlreadyExistFault",
            f"Subscription {subscription_name} already exists.",
        )


class SubscriptionNotFoundError(RDSClientError):
    def __init__(self, subscription_name):
        super().__init__(
            "SubscriptionNotFoundFault", f"Subscription {subscription_name} not found."
        )
