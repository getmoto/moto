from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import dms_backends
import json


class DatabaseMigrationServiceResponse(BaseResponse):
    SERVICE_NAME = "dms"

    @property
    def dms_backend(self):
        return dms_backends[self.region]

    # add methods from here

    def create_replication_task(self):
        replication_task_identifier = self._get_param("ReplicationTaskIdentifier")
        source_endpoint_arn = self._get_param("SourceEndpointArn")
        target_endpoint_arn = self._get_param("TargetEndpointArn")
        replication_instance_arn = self._get_param("ReplicationInstanceArn")
        migration_type = self._get_param("MigrationType")
        table_mappings = self._get_param("TableMappings")
        replication_task_settings = self._get_param("ReplicationTaskSettings")
        cdc_start_time = self._get_param("CdcStartTime")
        cdc_start_position = self._get_param("CdcStartPosition")
        cdc_stop_position = self._get_param("CdcStopPosition")
        tags = self._get_list_prefix("Tags.member")
        task_data = self._get_param("TaskData")
        resource_identifier = self._get_param("ResourceIdentifier")
        replication_task = self.dms_backend.create_replication_task(
            replication_task_identifier=replication_task_identifier,
            source_endpoint_arn=source_endpoint_arn,
            target_endpoint_arn=target_endpoint_arn,
            replication_instance_arn=replication_instance_arn,
            migration_type=migration_type,
            table_mappings=table_mappings,
            replication_task_settings=replication_task_settings,
            cdc_start_time=cdc_start_time,
            cdc_start_position=cdc_start_position,
            cdc_stop_position=cdc_stop_position,
            tags=tags,
            task_data=task_data,
            resource_identifier=resource_identifier,
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def start_replication_task(self):
        replication_task_arn = self._get_param("ReplicationTaskArn")
        start_replication_task_type = self._get_param("StartReplicationTaskType")
        cdc_start_time = self._get_param("CdcStartTime")
        cdc_start_position = self._get_param("CdcStartPosition")
        cdc_stop_position = self._get_param("CdcStopPosition")
        replication_task = self.dms_backend.start_replication_task(
            replication_task_arn=replication_task_arn,
            start_replication_task_type=start_replication_task_type,
            cdc_start_time=cdc_start_time,
            cdc_start_position=cdc_start_position,
            cdc_stop_position=cdc_stop_position,
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    # add templates from here

    def stop_replication_task(self):
        replication_task_arn = self._get_param("ReplicationTaskArn")
        replication_task = self.dms_backend.stop_replication_task(
            replication_task_arn=replication_task_arn,
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def delete_replication_task(self):
        replication_task_arn = self._get_param("ReplicationTaskArn")
        replication_task = self.dms_backend.delete_replication_task(
            replication_task_arn=replication_task_arn,
        )

        return json.dumps({"ReplicationTask": replication_task.to_dict()})

    def describe_replication_tasks(self):
        filters = self._get_list_prefix("Filters.member")
        max_records = self._get_int_param("MaxRecords")
        marker = self._get_param("Marker")
        without_settings = self._get_param("WithoutSettings")
        marker, replication_tasks = self.dms_backend.describe_replication_tasks(
            filters=filters, max_records=max_records, without_settings=without_settings,
        )

        return json.dumps(
            dict(
                marker=marker, ReplicationTasks=[t.to_dict() for t in replication_tasks]
            )
        )
