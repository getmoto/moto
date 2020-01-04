from boto3 import Session

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel

from .exceptions import InvalidRequestException


class Location(BaseModel):
    def __init__(
        self, location_uri, region_name=None, typ=None, metadata=None, arn_counter=0
    ):
        self.uri = location_uri
        self.region_name = region_name
        self.metadata = metadata
        self.typ = typ
        # Generate ARN
        self.arn = "arn:aws:datasync:{0}:111222333444:location/loc-{1}".format(
            region_name, str(arn_counter).zfill(17)
        )


class Task(BaseModel):
    def __init__(
        self,
        source_location_arn,
        destination_location_arn,
        name,
        region_name,
        arn_counter=0,
        metadata=None,
    ):
        self.source_location_arn = source_location_arn
        self.destination_location_arn = destination_location_arn
        self.name = name
        self.metadata = metadata
        # For simplicity Tasks are either available or running
        self.status = "AVAILABLE"
        self.current_task_execution_arn = None
        # Generate ARN
        self.arn = "arn:aws:datasync:{0}:111222333444:task/task-{1}".format(
            region_name, str(arn_counter).zfill(17)
        )


class TaskExecution(BaseModel):

    # For simplicity, task_execution can never fail
    # Some documentation refers to this list:
    # 'Status': 'QUEUED'|'LAUNCHING'|'PREPARING'|'TRANSFERRING'|'VERIFYING'|'SUCCESS'|'ERROR'
    # Others refers to this list:
    # INITIALIZING | PREPARING | TRANSFERRING | VERIFYING | SUCCESS/FAILURE
    # Checking with AWS Support...
    TASK_EXECUTION_INTERMEDIATE_STATES = (
        "INITIALIZING",
        # 'QUEUED', 'LAUNCHING',
        "PREPARING",
        "TRANSFERRING",
        "VERIFYING",
    )

    TASK_EXECUTION_FAILURE_STATES = ("ERROR",)
    TASK_EXECUTION_SUCCESS_STATES = ("SUCCESS",)
    # Also COMPLETED state?

    def __init__(self, task_arn, arn_counter=0):
        self.task_arn = task_arn
        self.arn = "{0}/execution/exec-{1}".format(task_arn, str(arn_counter).zfill(17))
        self.status = self.TASK_EXECUTION_INTERMEDIATE_STATES[0]

    # Simulate a task execution
    def iterate_status(self):
        if self.status in self.TASK_EXECUTION_FAILURE_STATES:
            return
        if self.status in self.TASK_EXECUTION_SUCCESS_STATES:
            return
        if self.status in self.TASK_EXECUTION_INTERMEDIATE_STATES:
            for i, status in enumerate(self.TASK_EXECUTION_INTERMEDIATE_STATES):
                if status == self.status:
                    if i < len(self.TASK_EXECUTION_INTERMEDIATE_STATES) - 1:
                        self.status = self.TASK_EXECUTION_INTERMEDIATE_STATES[i + 1]
                    else:
                        self.status = self.TASK_EXECUTION_SUCCESS_STATES[0]
                    return
        raise Exception(
            "TaskExecution.iterate_status: Unknown status={0}".format(self.status)
        )

    def cancel(self):
        if self.status not in self.TASK_EXECUTION_INTERMEDIATE_STATES:
            raise InvalidRequestException(
                "Sync task cannot be cancelled in its current status: {0}".format(
                    self.status
                )
            )
        self.status = "ERROR"


class DataSyncBackend(BaseBackend):
    def __init__(self, region_name):
        self.region_name = region_name
        # Always increase when new things are created
        # This ensures uniqueness
        self.arn_counter = 0
        self.locations = OrderedDict()
        self.tasks = OrderedDict()
        self.task_executions = OrderedDict()

    def reset(self):
        region_name = self.region_name
        self._reset_model_refs()
        self.__dict__ = {}
        self.__init__(region_name)

    def create_location(self, location_uri, typ=None, metadata=None):
        """
        # AWS DataSync allows for duplicate LocationUris
        for arn, location in self.locations.items():
            if location.uri == location_uri:
                raise Exception('Location already exists')
        """
        if not typ:
            raise Exception("Location type must be specified")
        self.arn_counter = self.arn_counter + 1
        location = Location(
            location_uri,
            region_name=self.region_name,
            arn_counter=self.arn_counter,
            metadata=metadata,
            typ=typ,
        )
        self.locations[location.arn] = location
        return location.arn

    def _get_location(self, location_arn, typ):
        if location_arn not in self.locations:
            raise InvalidRequestException(
                "Location {0} is not found.".format(location_arn)
            )
        location = self.locations[location_arn]
        if location.typ != typ:
            raise InvalidRequestException(
                "Invalid Location type: {0}".format(location.typ)
            )
        return location

    def delete_location(self, location_arn):
        if location_arn in self.locations:
            del self.locations[location_arn]
        else:
            raise InvalidRequestException

    def create_task(
        self, source_location_arn, destination_location_arn, name, metadata=None
    ):
        if source_location_arn not in self.locations:
            raise InvalidRequestException(
                "Location {0} not found.".format(source_location_arn)
            )
        if destination_location_arn not in self.locations:
            raise InvalidRequestException(
                "Location {0} not found.".format(destination_location_arn)
            )
        self.arn_counter = self.arn_counter + 1
        task = Task(
            source_location_arn,
            destination_location_arn,
            name,
            region_name=self.region_name,
            arn_counter=self.arn_counter,
            metadata=metadata,
        )
        self.tasks[task.arn] = task
        return task.arn

    def _get_task(self, task_arn):
        if task_arn in self.tasks:
            return self.tasks[task_arn]
        else:
            raise InvalidRequestException

    def update_task(self, task_arn, name, metadata):
        if task_arn in self.tasks:
            task = self.tasks[task_arn]
            task.name = name
            task.metadata = metadata
        else:
            raise InvalidRequestException(
                "Sync task {0} is not found.".format(task_arn)
            )

    def delete_task(self, task_arn):
        if task_arn in self.tasks:
            del self.tasks[task_arn]
        else:
            raise InvalidRequestException

    def start_task_execution(self, task_arn):
        self.arn_counter = self.arn_counter + 1
        if task_arn in self.tasks:
            task = self.tasks[task_arn]
            if task.status == "AVAILABLE":
                task_execution = TaskExecution(task_arn, arn_counter=self.arn_counter)
                self.task_executions[task_execution.arn] = task_execution
                self.tasks[task_arn].current_task_execution_arn = task_execution.arn
                self.tasks[task_arn].status = "RUNNING"
                return task_execution.arn
        raise InvalidRequestException("Invalid request.")

    def _get_task_execution(self, task_execution_arn):
        if task_execution_arn in self.task_executions:
            return self.task_executions[task_execution_arn]
        else:
            raise InvalidRequestException

    def cancel_task_execution(self, task_execution_arn):
        if task_execution_arn in self.task_executions:
            task_execution = self.task_executions[task_execution_arn]
            task_execution.cancel()
            task_arn = task_execution.task_arn
            self.tasks[task_arn].current_task_execution_arn = None
            self.tasks[task_arn].status = "AVAILABLE"
            return
        raise InvalidRequestException(
            "Sync task {0} is not found.".format(task_execution_arn)
        )


datasync_backends = {}
for region in Session().get_available_regions("datasync"):
    datasync_backends[region] = DataSyncBackend(region)
for region in Session().get_available_regions("datasync", partition_name="aws-us-gov"):
    datasync_backends[region] = DataSyncBackend(region)
for region in Session().get_available_regions("datasync", partition_name="aws-cn"):
    datasync_backends[region] = DataSyncBackend(region)
