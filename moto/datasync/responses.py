import json

from moto.core.responses import BaseResponse

from .exceptions import InvalidRequestException
from .models import datasync_backends


class DataSyncResponse(BaseResponse):
    @property
    def datasync_backend(self):
        return datasync_backends[self.region]

    def list_locations(self):
        locations = list()
        for arn, location in self.datasync_backend.locations.items():
            locations.append({"LocationArn": location.arn, "LocationUri": location.uri})
        return json.dumps({"Locations": locations})

    def _get_location(self, location_arn, typ):
        location_arn = self._get_param("LocationArn")
        if location_arn not in self.datasync_backend.locations:
            raise InvalidRequestException(
                "Location {0} is not found.".format(location_arn)
            )
        location = self.datasync_backend.locations[location_arn]
        if location.typ != typ:
            raise InvalidRequestException(
                "Invalid Location type: {0}".format(location.typ)
            )
        return location

    def create_location_s3(self):
        # s3://bucket_name/folder/
        s3_bucket_arn = self._get_param("S3BucketArn")
        subdirectory = self._get_param("Subdirectory")
        metadata = {"S3Config": self._get_param("S3Config")}
        location_uri_elts = ["s3:/", s3_bucket_arn.split(":")[-1]]
        if subdirectory:
            location_uri_elts.append(subdirectory)
        location_uri = "/".join(location_uri_elts)
        arn = self.datasync_backend.create_location(
            location_uri, metadata=metadata, typ="S3"
        )
        return json.dumps({"LocationArn": arn})

    def describe_location_s3(self):
        location_arn = self._get_param("LocationArn")
        location = self._get_location(location_arn, typ="S3")
        return json.dumps(
            {
                "LocationArn": location.arn,
                "LocationUri": location.uri,
                "S3Config": location.metadata["S3Config"],
            }
        )

    def create_location_smb(self):
        # smb://smb.share.fqdn/AWS_Test/
        subdirectory = self._get_param("Subdirectory")
        server_hostname = self._get_param("ServerHostname")
        metadata = {
            "AgentArns": self._get_param("AgentArns"),
            "User": self._get_param("User"),
            "Domain": self._get_param("Domain"),
            "MountOptions": self._get_param("MountOptions"),
        }

        location_uri = "/".join(["smb:/", server_hostname, subdirectory])
        arn = self.datasync_backend.create_location(
            location_uri, metadata=metadata, typ="SMB"
        )
        return json.dumps({"LocationArn": arn})

    def describe_location_smb(self):
        location_arn = self._get_param("LocationArn")
        location = self._get_location(location_arn, typ="SMB")
        return json.dumps(
            {
                "LocationArn": location.arn,
                "LocationUri": location.uri,
                "AgentArns": location.metadata["AgentArns"],
                "User": location.metadata["User"],
                "Domain": location.metadata["Domain"],
                "MountOptions": location.metadata["MountOptions"],
            }
        )

    def create_task(self):
        destination_location_arn = self._get_param("DestinationLocationArn")
        source_location_arn = self._get_param("SourceLocationArn")
        name = self._get_param("Name")

        arn = self.datasync_backend.create_task(
            source_location_arn, destination_location_arn, name
        )
        return json.dumps({"TaskArn": arn})

    def list_tasks(self):
        tasks = list()
        for arn, task in self.datasync_backend.tasks.items():
            tasks.append(
                {"Name": task.name, "Status": task.status, "TaskArn": task.arn}
            )
        return json.dumps({"Tasks": tasks})

    def describe_task(self):
        task_arn = self._get_param("TaskArn")
        if task_arn in self.datasync_backend.tasks:
            task = self.datasync_backend.tasks[task_arn]
            return json.dumps(
                {
                    "TaskArn": task.arn,
                    "Name": task.name,
                    "CurrentTaskExecutionArn": task.current_task_execution_arn,
                    "Status": task.status,
                    "SourceLocationArn": task.source_location_arn,
                    "DestinationLocationArn": task.destination_location_arn,
                }
            )
        raise InvalidRequestException

    def start_task_execution(self):
        task_arn = self._get_param("TaskArn")
        if task_arn in self.datasync_backend.tasks:
            arn = self.datasync_backend.start_task_execution(task_arn)
            if arn:
                return json.dumps({"TaskExecutionArn": arn})
        raise InvalidRequestException("Invalid request.")

    def cancel_task_execution(self):
        task_execution_arn = self._get_param("TaskExecutionArn")
        self.datasync_backend.cancel_task_execution(task_execution_arn)
        return json.dumps({})

    def describe_task_execution(self):
        task_execution_arn = self._get_param("TaskExecutionArn")

        if task_execution_arn in self.datasync_backend.task_executions:
            task_execution = self.datasync_backend.task_executions[task_execution_arn]
            if task_execution:
                result = json.dumps(
                    {
                        "TaskExecutionArn": task_execution.arn,
                        "Status": task_execution.status,
                    }
                )
                if task_execution.status == "SUCCESS":
                    self.datasync_backend.tasks[
                        task_execution.task_arn
                    ].status = "AVAILABLE"
                # Simulate task being executed
                task_execution.iterate_status()
                return result
        raise InvalidRequestException
