from __future__ import unicode_literals

import json

from boto3 import Session
from datetime import datetime
from moto.core import ACCOUNT_ID, BaseBackend, BaseModel

from .exceptions import (
    InvalidResourceStateFault,
    ResourceAlreadyExistsFault,
    ResourceNotFoundFault,
)
from .utils import filter_tasks


class DatabaseMigrationServiceBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(DatabaseMigrationServiceBackend, self).__init__()
        self.region_name = region_name
        self.replication_tasks = {}

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "dms"
        )

    def create_replication_task(
        self,
        replication_task_identifier,
        source_endpoint_arn,
        target_endpoint_arn,
        replication_instance_arn,
        migration_type,
        table_mappings,
        replication_task_settings,
        cdc_start_time,
        cdc_start_position,
        cdc_stop_position,
        tags,
        task_data,
        resource_identifier,
    ):
        replication_task = FakeReplicationTask(
            replication_task_identifier=replication_task_identifier,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
            replication_instance_arn=replication_instance_arn,
            migration_type=migration_type,
            table_mappings=table_mappings,
            replication_task_settings=replication_task_settings,
            region_name=self.region_name,
        )

        if self.replication_tasks.get(replication_task.arn):
            raise ResourceAlreadyExistsFault(
                "The resource you are attempting to create already exists."
            )

        self.replication_tasks[replication_task.arn] = replication_task

        return replication_task

    def start_replication_task(
        self,
        replication_task_arn,
        start_replication_task_type,
        cdc_start_time,
        cdc_start_position,
        cdc_stop_position,
    ):
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        return self.replication_tasks[replication_task_arn].start()

    def stop_replication_task(self, replication_task_arn):
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        return self.replication_tasks[replication_task_arn].stop()

    def delete_replication_task(self, replication_task_arn):
        if not self.replication_tasks.get(replication_task_arn):
            raise ResourceNotFoundFault("Replication task could not be found.")

        task = self.replication_tasks[replication_task_arn]
        task.delete()
        self.replication_tasks.pop(replication_task_arn)

        return task

    def describe_replication_tasks(self, filters, max_records, without_settings):
        replication_tasks = filter_tasks(self.replication_tasks.values(), filters)

        if max_records and max_records > 0:
            replication_tasks = replication_tasks[:max_records]

        return None, replication_tasks


class FakeReplicationTask(BaseModel):
    def __init__(
        self,
        replication_task_identifier,
        migration_type,
        replication_instance_arn,
        source_endpoint_arn,
        target_endpoint_arn,
        table_mappings,
        replication_task_settings,
        region_name,
    ):
        self.id = replication_task_identifier
        self.region = region_name
        self.migration_type = migration_type
        self.replication_instance_arn = replication_instance_arn
        self.source_endpoint_arn = source_endpoint_arn
        self.target_endpoint_arn = target_endpoint_arn
        self.table_mappings = table_mappings
        self.replication_task_settings = replication_task_settings

        self.status = "creating"

        self.creation_date = datetime.utcnow()
        self.start_date = None
        self.stop_date = None

    @property
    def arn(self):
        return "arn:aws:dms:{region}:{account_id}:task:{task_id}".format(
            region=self.region, account_id=ACCOUNT_ID, task_id=self.id
        )

    def to_dict(self):
        start_date = self.start_date.isoformat() if self.start_date else None
        stop_date = self.stop_date.isoformat() if self.stop_date else None

        return {
            "ReplicationTaskIdentifier": self.id,
            "SourceEndpointArn": self.source_endpoint_arn,
            "TargetEndpointArn": self.target_endpoint_arn,
            "ReplicationInstanceArn": self.replication_instance_arn,
            "MigrationType": self.migration_type,
            "TableMappings": json.dumps(self.table_mappings),
            "ReplicationTaskSettings": json.dumps(self.replication_task_settings),
            "Status": self.status,
            "ReplicationTaskCreationDate": self.creation_date.isoformat(),
            "ReplicationTaskStartDate": start_date,
            "ReplicationTaskArn": self.arn,
            "ReplicationTaskStats": {
                "FullLoadProgressPercent": 100,
                "ElapsedTimeMillis": 100,
                "TablesLoaded": 1,
                "TablesLoading": 0,
                "TablesQueued": 0,
                "TablesErrored": 0,
                "FreshStartDate": start_date,
                "StartDate": start_date,
                "StopDate": stop_date,
                "FullLoadStartDate": start_date,
                "FullLoadFinishDate": stop_date,
            },
        }

    def ready(self):
        self.status = "ready"
        return self

    def start(self):
        self.status = "starting"
        self.start_date = datetime.utcnow()
        self.run()
        return self

    def stop(self):
        if self.status != "running":
            raise InvalidResourceStateFault("Replication task is not running")

        self.status = "stopped"
        self.stop_date = datetime.utcnow()
        return self

    def delete(self):
        self.status = "deleting"
        return self

    def run(self):
        self.status = "running"
        return self


dms_backends = {}
for region in Session().get_available_regions("dms"):
    dms_backends[region] = DatabaseMigrationServiceBackend()
for region in Session().get_available_regions("dms", partition_name="aws-us-gov"):
    dms_backends[region] = DatabaseMigrationServiceBackend()
for region in Session().get_available_regions("dms", partition_name="aws-cn"):
    dms_backends[region] = DatabaseMigrationServiceBackend()
