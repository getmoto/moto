from collections import OrderedDict
from moto.core import BaseBackend, BackendDict, BaseModel

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
        self.arn = f"arn:aws:datasync:{region_name}:111222333444:location/loc-{str(arn_counter).zfill(17)}"


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
        self.arn = f"arn:aws:datasync:{region_name}:111222333444:task/task-{str(arn_counter).zfill(17)}"


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
        self.arn = f"{task_arn}/execution/exec-{str(arn_counter).zfill(17)}"
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
        raise Exception(f"TaskExecution.iterate_status: Unknown status={self.status}")

    def cancel(self):
        if self.status not in self.TASK_EXECUTION_INTERMEDIATE_STATES:
            raise InvalidRequestException(
                f"Sync task cannot be cancelled in its current status: {self.status}"
            )
        self.status = "ERROR"


class DataSyncBackend(BaseBackend):
    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        # Always increase when new things are created
        # This ensures uniqueness
        self.arn_counter = 0
        self.locations = OrderedDict()
        self.tasks = OrderedDict()
        self.task_executions = OrderedDict()

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "datasync"
        )

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
            raise InvalidRequestException(f"Location {location_arn} is not found.")
        location = self.locations[location_arn]
        if location.typ != typ:
            raise InvalidRequestException(f"Invalid Location type: {location.typ}")
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
            raise InvalidRequestException(f"Location {source_location_arn} not found.")
        if destination_location_arn not in self.locations:
            raise InvalidRequestException(
                f"Location {destination_location_arn} not found."
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
            raise InvalidRequestException(f"Sync task {task_arn} is not found.")

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
        raise InvalidRequestException(f"Sync task {task_execution_arn} is not found.")


datasync_backends = BackendDict(DataSyncBackend, "datasync")
