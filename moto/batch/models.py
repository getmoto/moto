import re
from itertools import cycle
from time import sleep
import datetime
import time
import uuid
import logging
import threading
import dateutil.parser
from sys import platform

from moto.core import BaseBackend, BaseModel, CloudFormationModel, get_account_id
from moto.iam import iam_backends
from moto.ec2 import ec2_backends
from moto.ecs import ecs_backends
from moto.logs import logs_backends
from moto.utilities.tagging_service import TaggingService

from .exceptions import InvalidParameterValueException, ClientException, ValidationError
from .utils import (
    make_arn_for_compute_env,
    make_arn_for_job_queue,
    make_arn_for_task_def,
    lowercase_first_key,
)
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.ec2.models.instance_types import INSTANCE_TYPES as EC2_INSTANCE_TYPES
from moto.ec2.models.instance_types import INSTANCE_FAMILIES as EC2_INSTANCE_FAMILIES
from moto.iam.exceptions import IAMNotFoundException
from moto.core.utils import unix_time_millis, BackendDict
from moto.moto_api import state_manager
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.docker_utilities import DockerModel
from moto import settings

logger = logging.getLogger(__name__)
COMPUTE_ENVIRONMENT_NAME_REGEX = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{1,126}[A-Za-z0-9]$"
)


def datetime2int_milliseconds(date):
    """
    AWS returns timestamps in milliseconds
    We don't use milliseconds timestamps internally,
    this method should be used only in describe() method
    """
    return int(date.timestamp() * 1000)


def datetime2int(date):
    return int(time.mktime(date.timetuple()))


class ComputeEnvironment(CloudFormationModel):
    def __init__(
        self,
        compute_environment_name,
        _type,
        state,
        compute_resources,
        service_role,
        region_name,
    ):
        self.name = compute_environment_name
        self.env_type = _type
        self.state = state
        self.compute_resources = compute_resources
        self.service_role = service_role
        self.arn = make_arn_for_compute_env(
            get_account_id(), compute_environment_name, region_name
        )

        self.instances = []
        self.ecs_arn = None
        self.ecs_name = None

    def add_instance(self, instance):
        self.instances.append(instance)

    def set_ecs(self, arn, name):
        self.ecs_arn = arn
        self.ecs_name = name

    @property
    def physical_resource_id(self):
        return self.arn

    @staticmethod
    def cloudformation_name_type():
        return "ComputeEnvironmentName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-batch-computeenvironment.html
        return "AWS::Batch::ComputeEnvironment"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        backend = batch_backends[region_name]
        properties = cloudformation_json["Properties"]

        env = backend.create_compute_environment(
            resource_name,
            properties["Type"],
            properties.get("State", "ENABLED"),
            lowercase_first_key(properties["ComputeResources"]),
            properties["ServiceRole"],
        )
        arn = env[1]

        return backend.get_compute_environment_by_arn(arn)


class JobQueue(CloudFormationModel):
    def __init__(
        self,
        name,
        priority,
        state,
        environments,
        env_order_json,
        region_name,
        backend,
        tags=None,
    ):
        """
        :param name: Job queue name
        :type name: str
        :param priority: Job queue priority
        :type priority: int
        :param state: Either ENABLED or DISABLED
        :type state: str
        :param environments: Compute Environments
        :type environments: list of ComputeEnvironment
        :param env_order_json: Compute Environments JSON for use when describing
        :type env_order_json: list of dict
        :param region_name: Region name
        :type region_name: str
        """
        self.name = name
        self.priority = priority
        self.state = state
        self.environments = environments
        self.env_order_json = env_order_json
        self.arn = make_arn_for_job_queue(get_account_id(), name, region_name)
        self.status = "VALID"
        self.backend = backend

        if tags:
            backend.tag_resource(self.arn, tags)

        self.jobs = []

    def describe(self):
        result = {
            "computeEnvironmentOrder": self.env_order_json,
            "jobQueueArn": self.arn,
            "jobQueueName": self.name,
            "priority": self.priority,
            "state": self.state,
            "status": self.status,
            "tags": self.backend.list_tags_for_resource(self.arn),
        }

        return result

    @property
    def physical_resource_id(self):
        return self.arn

    @staticmethod
    def cloudformation_name_type():
        return "JobQueueName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-batch-jobqueue.html
        return "AWS::Batch::JobQueue"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        backend = batch_backends[region_name]
        properties = cloudformation_json["Properties"]

        # Need to deal with difference case from cloudformation compute_resources, e.g. instanceRole vs InstanceRole
        # Hacky fix to normalise keys, is making me think I want to start spamming cAsEiNsEnSiTiVe dictionaries
        compute_envs = [
            lowercase_first_key(dict_item)
            for dict_item in properties["ComputeEnvironmentOrder"]
        ]

        queue = backend.create_job_queue(
            queue_name=resource_name,
            priority=properties["Priority"],
            state=properties.get("State", "ENABLED"),
            compute_env_order=compute_envs,
        )
        arn = queue[1]

        return backend.get_job_queue_by_arn(arn)


class JobDefinition(CloudFormationModel):
    def __init__(
        self,
        name,
        parameters,
        _type,
        container_properties,
        region_name,
        tags=None,
        revision=0,
        retry_strategy=0,
        timeout=None,
        backend=None,
        platform_capabilities=None,
        propagate_tags=None,
    ):
        self.name = name
        self.retry_strategy = retry_strategy
        self.type = _type
        self.revision = revision
        self._region = region_name
        self.container_properties = container_properties
        self.arn = None
        self.status = "ACTIVE"
        self.parameters = parameters or {}
        self.timeout = timeout
        self.backend = backend
        self.platform_capabilities = platform_capabilities
        self.propagate_tags = propagate_tags

        if "resourceRequirements" not in self.container_properties:
            self.container_properties["resourceRequirements"] = []
        if "secrets" not in self.container_properties:
            self.container_properties["secrets"] = []

        self._validate()
        self._update_arn()

        tags = self._format_tags(tags or {})
        # Validate the tags before proceeding.
        errmsg = self.backend.tagger.validate_tags(tags)
        if errmsg:
            raise ValidationError(errmsg)

        self.backend.tagger.tag_resource(self.arn, tags)

    def _format_tags(self, tags):
        return [{"Key": k, "Value": v} for k, v in tags.items()]

    def _update_arn(self):
        self.revision += 1
        self.arn = make_arn_for_task_def(
            get_account_id(), self.name, self.revision, self._region
        )

    def _get_resource_requirement(self, req_type, default=None):
        """
        Get resource requirement from container properties.

        Resource requirements like "memory" and "vcpus" are now specified in
        "resourceRequirements". This function retrieves a resource requirement
        from either container_properties.resourceRequirements (preferred) or
        directly from container_properties (deprecated).

        :param req_type: The type of resource requirement to retrieve.
        :type req_type: ["gpu", "memory", "vcpus"]

        :param default: The default value to return if the resource requirement is not found.
        :type default: any, default=None

        :return: The value of the resource requirement, or None.
        :rtype: any
        """
        resource_reqs = self.container_properties.get("resourceRequirements", [])

        # Filter the resource requirements by the specified type.
        # Note that VCPUS are specified in resourceRequirements without the
        # trailing "s", so we strip that off in the comparison below.
        required_resource = list(
            filter(
                lambda req: req["type"].lower() == req_type.lower().rstrip("s"),
                resource_reqs,
            )
        )

        if required_resource:
            if req_type == "vcpus":
                return float(required_resource[0]["value"])
            elif req_type == "memory":
                return int(required_resource[0]["value"])
            else:
                return required_resource[0]["value"]
        else:
            return self.container_properties.get(req_type, default)

    def _validate(self):
        # For future use when containers arnt the only thing in batch
        if self.type not in ("container",):
            raise ClientException('type must be one of "container"')

        if not isinstance(self.parameters, dict):
            raise ClientException("parameters must be a string to string map")

        if "image" not in self.container_properties:
            raise ClientException("containerProperties must contain image")

        memory = self._get_resource_requirement("memory")
        if memory is None:
            raise ClientException("containerProperties must contain memory")
        if memory < 4:
            raise ClientException("container memory limit must be greater than 4")

        vcpus = self._get_resource_requirement("vcpus")
        if vcpus is None:
            raise ClientException("containerProperties must contain vcpus")
        if vcpus <= 0:
            raise ClientException("container vcpus limit must be greater than 0")

    def deregister(self):
        self.status = "INACTIVE"

    def update(
        self, parameters, _type, container_properties, retry_strategy, tags, timeout
    ):
        if self.status != "INACTIVE":
            if parameters is None:
                parameters = self.parameters

            if _type is None:
                _type = self.type

            if container_properties is None:
                container_properties = self.container_properties

            if retry_strategy is None:
                retry_strategy = self.retry_strategy

        return JobDefinition(
            self.name,
            parameters,
            _type,
            container_properties,
            region_name=self._region,
            revision=self.revision,
            retry_strategy=retry_strategy,
            tags=tags,
            timeout=timeout,
            backend=self.backend,
            platform_capabilities=self.platform_capabilities,
            propagate_tags=self.propagate_tags,
        )

    def describe(self):
        result = {
            "jobDefinitionArn": self.arn,
            "jobDefinitionName": self.name,
            "parameters": self.parameters,
            "revision": self.revision,
            "status": self.status,
            "type": self.type,
            "tags": self.backend.tagger.get_tag_dict_for_resource(self.arn),
            "platformCapabilities": self.platform_capabilities,
            "retryStrategy": self.retry_strategy,
            "propagateTags": self.propagate_tags,
        }
        if self.container_properties is not None:
            result["containerProperties"] = self.container_properties
        if self.timeout:
            result["timeout"] = self.timeout

        return result

    @property
    def physical_resource_id(self):
        return self.arn

    @staticmethod
    def cloudformation_name_type():
        return "JobDefinitionName"

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-batch-jobdefinition.html
        return "AWS::Batch::JobDefinition"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        backend = batch_backends[region_name]
        properties = cloudformation_json["Properties"]
        res = backend.register_job_definition(
            def_name=resource_name,
            parameters=lowercase_first_key(properties.get("Parameters", {})),
            _type="container",
            tags=lowercase_first_key(properties.get("Tags", {})),
            retry_strategy=lowercase_first_key(properties["RetryStrategy"]),
            container_properties=lowercase_first_key(properties["ContainerProperties"]),
            timeout=lowercase_first_key(properties.get("timeout", {})),
            platform_capabilities=None,
            propagate_tags=None,
        )
        arn = res[1]

        return backend.get_job_definition_by_arn(arn)


class Job(threading.Thread, BaseModel, DockerModel, ManagedState):
    def __init__(
        self,
        name,
        job_def,
        job_queue,
        log_backend,
        container_overrides,
        depends_on,
        all_jobs,
        timeout,
    ):
        """
        Docker Job

        :param name: Job Name
        :param job_def: Job definition
        :type: job_def: JobDefinition
        :param job_queue: Job Queue
        :param log_backend: Log backend
        :type log_backend: moto.logs.models.LogsBackend
        """
        threading.Thread.__init__(self)
        DockerModel.__init__(self)
        ManagedState.__init__(
            self,
            "batch::job",
            [
                ("SUBMITTED", "PENDING"),
                ("PENDING", "RUNNABLE"),
                ("RUNNABLE", "STARTING"),
                ("STARTING", "RUNNING"),
            ],
        )

        self.job_name = name
        self.job_id = str(uuid.uuid4())
        self.job_definition = job_def
        self.container_overrides = container_overrides or {}
        self.job_queue = job_queue
        self.job_queue.jobs.append(self)
        self.job_created_at = datetime.datetime.now()
        self.job_started_at = datetime.datetime(1970, 1, 1)
        self.job_stopped_at = datetime.datetime(1970, 1, 1)
        self.job_stopped = False
        self.job_stopped_reason = None
        self.depends_on = depends_on
        self.timeout = timeout
        self.all_jobs = all_jobs

        self.stop = False
        self.exit_code = None

        self.daemon = True
        self.name = "MOTO-BATCH-" + self.job_id

        self._log_backend = log_backend
        self.log_stream_name = None

        self.attempts = []
        self.latest_attempt = None

    def describe_short(self):
        result = {
            "jobId": self.job_id,
            "jobName": self.job_name,
            "createdAt": datetime2int_milliseconds(self.job_created_at),
            "status": self.status,
            "jobDefinition": self.job_definition.arn,
        }
        if self.job_stopped_reason is not None:
            result["statusReason"] = self.job_stopped_reason
        if result["status"] not in ["SUBMITTED", "PENDING", "RUNNABLE", "STARTING"]:
            result["startedAt"] = datetime2int_milliseconds(self.job_started_at)
        if self.job_stopped:
            result["stoppedAt"] = datetime2int_milliseconds(self.job_stopped_at)
            if self.exit_code is not None:
                result["container"] = {"exitCode": self.exit_code}
        return result

    def describe(self):
        result = self.describe_short()
        result["jobQueue"] = self.job_queue.arn
        result["dependsOn"] = self.depends_on if self.depends_on else []
        if self.job_stopped:
            result["stoppedAt"] = datetime2int_milliseconds(self.job_stopped_at)
            result["container"] = {}
            result["container"]["command"] = self._get_container_property("command", [])
            result["container"]["privileged"] = self._get_container_property(
                "privileged", False
            )
            result["container"][
                "readonlyRootFilesystem"
            ] = self._get_container_property("readonlyRootFilesystem", False)
            result["container"]["ulimits"] = self._get_container_property("ulimits", {})
            result["container"]["vcpus"] = self._get_container_property("vcpus", 1)
            result["container"]["memory"] = self._get_container_property("memory", 512)
            result["container"]["volumes"] = self._get_container_property("volumes", [])
            result["container"]["environment"] = self._get_container_property(
                "environment", []
            )
            result["container"]["logStreamName"] = self.log_stream_name
        if self.timeout:
            result["timeout"] = self.timeout
        result["attempts"] = self.attempts
        return result

    def _get_container_property(self, p, default):
        if p == "environment":
            job_env = self.container_overrides.get(p, default)
            jd_env = self.job_definition.container_properties.get(p, default)

            job_env_dict = {_env["name"]: _env["value"] for _env in job_env}
            jd_env_dict = {_env["name"]: _env["value"] for _env in jd_env}

            for key in jd_env_dict.keys():
                if key not in job_env_dict.keys():
                    job_env.append({"name": key, "value": jd_env_dict[key]})

            job_env.append({"name": "AWS_BATCH_JOB_ID", "value": self.job_id})

            return job_env

        if p in ["vcpus", "memory"]:
            return self.container_overrides.get(
                p, self.job_definition._get_resource_requirement(p, default)
            )

        return self.container_overrides.get(
            p, self.job_definition.container_properties.get(p, default)
        )

    def _get_attempt_duration(self):
        if self.timeout:
            return self.timeout["attemptDurationSeconds"]
        if self.job_definition.timeout:
            return self.job_definition.timeout["attemptDurationSeconds"]
        return None

    def run(self):
        """
        Run the container.

        Logic is as follows:
        Generate container info (eventually from task definition)
        Start container
        Loop whilst not asked to stop and the container is running.
          Get all logs from container between the last time I checked and now.
        Convert logs into cloudwatch format
        Put logs into cloudwatch

        :return:
        """
        try:
            import docker

            self.advance()
            while self.status == "SUBMITTED":
                # Wait until we've moved onto state 'PENDING'
                sleep(0.5)

            # Wait until all dependent jobs have finished
            # If any of the dependent jobs have failed, not even start
            if self.depends_on and not self._wait_for_dependencies():
                return

            image = self.job_definition.container_properties.get(
                "image", "alpine:latest"
            )
            privileged = self.job_definition.container_properties.get(
                "privileged", False
            )
            cmd = self._get_container_property(
                "command",
                '/bin/sh -c "for a in `seq 1 10`; do echo Hello World; sleep 1; done"',
            )
            environment = {
                e["name"]: e["value"]
                for e in self._get_container_property("environment", [])
            }
            volumes = {
                v["name"]: v["host"]
                for v in self._get_container_property("volumes", [])
            }
            mounts = [
                docker.types.Mount(
                    m["containerPath"],
                    volumes[m["sourceVolume"]]["sourcePath"],
                    type="bind",
                    read_only=m["readOnly"],
                )
                for m in self._get_container_property("mountPoints", [])
            ]
            name = "{0}-{1}".format(self.job_name, self.job_id)

            self.advance()
            while self.status == "PENDING":
                # Wait until the state is no longer pending, but 'RUNNABLE'
                sleep(0.5)
            # TODO setup ecs container instance

            self.job_started_at = datetime.datetime.now()
            self._start_attempt()

            # add host.docker.internal host on linux to emulate Mac + Windows behavior
            #   for communication with other mock AWS services running on localhost
            extra_hosts = (
                {"host.docker.internal": "host-gateway"}
                if platform == "linux" or platform == "linux2"
                else {}
            )

            environment["MOTO_HOST"] = settings.moto_server_host()
            environment["MOTO_PORT"] = settings.moto_server_port()
            environment[
                "MOTO_HTTP_ENDPOINT"
            ] = f'{environment["MOTO_HOST"]}:{environment["MOTO_PORT"]}'

            run_kwargs = dict()
            network_name = settings.moto_network_name()
            network_mode = settings.moto_network_mode()
            if network_name:
                run_kwargs["network"] = network_name
            elif network_mode:
                run_kwargs["network_mode"] = network_mode

            log_config = docker.types.LogConfig(type=docker.types.LogConfig.types.JSON)
            self.advance()
            while self.status == "RUNNABLE":
                # Wait until the state is no longer runnable, but 'STARTING'
                sleep(0.5)

            self.advance()
            while self.status == "STARTING":
                # Wait until the state is no longer runnable, but 'RUNNING'
                sleep(0.5)
            container = self.docker_client.containers.run(
                image,
                cmd,
                detach=True,
                name=name,
                log_config=log_config,
                environment=environment,
                mounts=mounts,
                privileged=privileged,
                extra_hosts=extra_hosts,
                **run_kwargs,
            )
            try:
                container.reload()

                max_time = None
                if self._get_attempt_duration():
                    attempt_duration = self._get_attempt_duration()
                    max_time = self.job_started_at + datetime.timedelta(
                        seconds=attempt_duration
                    )

                while container.status == "running" and not self.stop:
                    container.reload()
                    time.sleep(0.5)

                    if max_time and datetime.datetime.now() > max_time:
                        raise Exception(
                            "Job time exceeded the configured attemptDurationSeconds"
                        )

                # Container should be stopped by this point... unless asked to stop
                if container.status == "running":
                    container.kill()

                # Log collection
                logs_stdout = []
                logs_stderr = []
                logs_stderr.extend(
                    container.logs(
                        stdout=False,
                        stderr=True,
                        timestamps=True,
                        since=datetime2int(self.job_started_at),
                    )
                    .decode()
                    .split("\n")
                )
                logs_stdout.extend(
                    container.logs(
                        stdout=True,
                        stderr=False,
                        timestamps=True,
                        since=datetime2int(self.job_started_at),
                    )
                    .decode()
                    .split("\n")
                )

                # Process logs
                logs_stdout = [x for x in logs_stdout if len(x) > 0]
                logs_stderr = [x for x in logs_stderr if len(x) > 0]
                logs = []
                for line in logs_stdout + logs_stderr:
                    date, line = line.split(" ", 1)
                    date_obj = (
                        dateutil.parser.parse(date)
                        .astimezone(datetime.timezone.utc)
                        .replace(tzinfo=None)
                    )
                    date = unix_time_millis(date_obj)
                    logs.append({"timestamp": date, "message": line.strip()})
                logs = sorted(logs, key=lambda l: l["timestamp"])

                # Send to cloudwatch
                log_group = "/aws/batch/job"
                stream_name = "{0}/default/{1}".format(
                    self.job_definition.name, self.job_id
                )
                self.log_stream_name = stream_name
                self._log_backend.ensure_log_group(log_group, None)
                self._log_backend.create_log_stream(log_group, stream_name)
                self._log_backend.put_log_events(log_group, stream_name, logs)

                result = container.wait() or {}
                self.exit_code = result.get("StatusCode", 0)
                job_failed = self.stop or self.exit_code > 0
                self._mark_stopped(success=not job_failed)

            except Exception as err:
                logger.error(
                    "Failed to run AWS Batch container {0}. Error {1}".format(
                        self.name, err
                    )
                )
                self._mark_stopped(success=False)
                container.kill()
            finally:
                container.remove()
        except Exception as err:
            logger.error(
                "Failed to run AWS Batch container {0}. Error {1}".format(
                    self.name, err
                )
            )
            self._mark_stopped(success=False)

    def _mark_stopped(self, success=True):
        # Ensure that job_stopped/job_stopped_at-attributes are set first
        # The describe-method needs them immediately when status is set
        self.job_stopped = True
        self.job_stopped_at = datetime.datetime.now()
        self.status = "SUCCEEDED" if success else "FAILED"
        self._stop_attempt()

    def _start_attempt(self):
        self.latest_attempt = {
            "container": {
                "containerInstanceArn": "TBD",
                "logStreamName": self.log_stream_name,
                "networkInterfaces": [],
                "taskArn": self.job_definition.arn,
            }
        }
        self.latest_attempt["startedAt"] = datetime2int_milliseconds(
            self.job_started_at
        )
        self.attempts.append(self.latest_attempt)

    def _stop_attempt(self):
        if self.latest_attempt:
            self.latest_attempt["container"]["logStreamName"] = self.log_stream_name
            self.latest_attempt["stoppedAt"] = datetime2int_milliseconds(
                self.job_stopped_at
            )

    def terminate(self, reason):
        if not self.stop:
            self.stop = True
            self.job_stopped_reason = reason

    def _wait_for_dependencies(self):
        dependent_ids = [dependency["jobId"] for dependency in self.depends_on]
        successful_dependencies = set()
        while len(successful_dependencies) != len(dependent_ids):
            for dependent_id in dependent_ids:
                if dependent_id in self.all_jobs:
                    dependent_job = self.all_jobs[dependent_id]
                    if dependent_job.status == "SUCCEEDED":
                        successful_dependencies.add(dependent_id)
                    if dependent_job.status == "FAILED":
                        logger.error(
                            "Terminating job {0} due to failed dependency {1}".format(
                                self.name, dependent_job.name
                            )
                        )
                        self._mark_stopped(success=False)
                        return False

            time.sleep(1)
            if self.stop:
                # This job has been cancelled while it was waiting for a dependency
                self._mark_stopped(success=False)
                return False

        return True


class BatchBackend(BaseBackend):
    """
    Batch-jobs are executed inside a Docker-container. Everytime the `submit_job`-method is called, a new Docker container is started.
    A job is marked as 'Success' when the Docker-container exits without throwing an error.

    Use `@mock_batch_simple` instead if you do not want to use a Docker-container.
    With this decorator, jobs are simply marked as 'Success' without trying to execute any commands/scripts.
    """

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.tagger = TaggingService()

        self._compute_environments = {}
        self._job_queues = {}
        self._job_definitions = {}
        self._jobs = {}

        state_manager.register_default_transition(
            "batch::job", transition={"progression": "manual", "times": 1}
        )

    @property
    def iam_backend(self):
        """
        :return: IAM Backend
        :rtype: moto.iam.models.IAMBackend
        """
        return iam_backends["global"]

    @property
    def ec2_backend(self):
        """
        :return: EC2 Backend
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.region_name]

    @property
    def ecs_backend(self):
        """
        :return: ECS Backend
        :rtype: moto.ecs.models.EC2ContainerServiceBackend
        """
        return ecs_backends[self.region_name]

    @property
    def logs_backend(self):
        """
        :return: ECS Backend
        :rtype: moto.logs.models.LogsBackend
        """
        return logs_backends[self.region_name]

    def reset(self):
        for job in self._jobs.values():
            if job.status not in ("FAILED", "SUCCEEDED"):
                job.stop = True
                # Try to join
                job.join(0.2)

        super().reset()

    def get_compute_environment_by_arn(self, arn):
        return self._compute_environments.get(arn)

    def get_compute_environment_by_name(self, name):
        for comp_env in self._compute_environments.values():
            if comp_env.name == name:
                return comp_env
        return None

    def get_compute_environment(self, identifier):
        """
        Get compute environment by name or ARN
        :param identifier: Name or ARN
        :type identifier: str

        :return: Compute Environment or None
        :rtype: ComputeEnvironment or None
        """
        env = self.get_compute_environment_by_arn(identifier)
        if env is None:
            env = self.get_compute_environment_by_name(identifier)
        return env

    def get_job_queue_by_arn(self, arn):
        return self._job_queues.get(arn)

    def get_job_queue_by_name(self, name):
        for comp_env in self._job_queues.values():
            if comp_env.name == name:
                return comp_env
        return None

    def get_job_queue(self, identifier):
        """
        Get job queue by name or ARN
        :param identifier: Name or ARN
        :type identifier: str

        :return: Job Queue or None
        :rtype: JobQueue or None
        """
        env = self.get_job_queue_by_arn(identifier)
        if env is None:
            env = self.get_job_queue_by_name(identifier)
        return env

    def get_job_definition_by_arn(self, arn):
        return self._job_definitions.get(arn)

    def get_job_definition_by_name(self, name):
        latest_revision = -1
        latest_job = None
        for job_def in self._job_definitions.values():
            if job_def.name == name and job_def.revision > latest_revision:
                latest_job = job_def
                latest_revision = job_def.revision
        return latest_job

    def get_job_definition_by_name_revision(self, name, revision):
        for job_def in self._job_definitions.values():
            if job_def.name == name and job_def.revision == int(revision):
                return job_def
        return None

    def get_job_definition(self, identifier):
        """
        Get job definitions by name or ARN
        :param identifier: Name or ARN
        :type identifier: str

        :return: Job definition or None
        :rtype: JobDefinition or None
        """
        job_def = self.get_job_definition_by_arn(identifier)
        if job_def is None:
            if ":" in identifier:
                job_def = self.get_job_definition_by_name_revision(
                    *identifier.split(":", 1)
                )
            else:
                job_def = self.get_job_definition_by_name(identifier)
        return job_def

    def get_job_definitions(self, identifier):
        """
        Get job definitions by name or ARN
        :param identifier: Name or ARN
        :type identifier: str

        :return: Job definition or None
        :rtype: list of JobDefinition
        """
        result = []
        env = self.get_job_definition_by_arn(identifier)
        if env is not None:
            result.append(env)
        else:
            for value in self._job_definitions.values():
                if value.name == identifier:
                    result.append(value)

        return result

    def get_job_by_id(self, identifier):
        """
        Get job by id
        :param identifier: Job ID
        :type identifier: str

        :return: Job
        :rtype: Job
        """
        try:
            return self._jobs[identifier]
        except KeyError:
            return None

    def describe_compute_environments(self, environments=None):
        """
        Pagination is not yet implemented
        """
        envs = set()
        if environments is not None:
            envs = set(environments)

        result = []
        for arn, environment in self._compute_environments.items():
            # Filter shortcut
            if len(envs) > 0 and arn not in envs and environment.name not in envs:
                continue

            json_part = {
                "computeEnvironmentArn": arn,
                "computeEnvironmentName": environment.name,
                "ecsClusterArn": environment.ecs_arn,
                "serviceRole": environment.service_role,
                "state": environment.state,
                "type": environment.env_type,
                "status": "VALID",
                "statusReason": "Compute environment is available",
            }
            if environment.env_type == "MANAGED":
                json_part["computeResources"] = environment.compute_resources

            result.append(json_part)

        return result

    def create_compute_environment(
        self, compute_environment_name, _type, state, compute_resources, service_role
    ):
        # Validate
        if COMPUTE_ENVIRONMENT_NAME_REGEX.match(compute_environment_name) is None:
            raise InvalidParameterValueException(
                "Compute environment name does not match ^[A-Za-z0-9][A-Za-z0-9_-]{1,126}[A-Za-z0-9]$"
            )

        if self.get_compute_environment_by_name(compute_environment_name) is not None:
            raise InvalidParameterValueException(
                "A compute environment already exists with the name {0}".format(
                    compute_environment_name
                )
            )

        # Look for IAM role
        try:
            self.iam_backend.get_role_by_arn(service_role)
        except IAMNotFoundException:
            raise InvalidParameterValueException(
                "Could not find IAM role {0}".format(service_role)
            )

        if _type not in ("MANAGED", "UNMANAGED"):
            raise InvalidParameterValueException(
                "type {0} must be one of MANAGED | UNMANAGED".format(service_role)
            )

        if state is not None and state not in ("ENABLED", "DISABLED"):
            raise InvalidParameterValueException(
                "state {0} must be one of ENABLED | DISABLED".format(state)
            )

        if compute_resources is None and _type == "MANAGED":
            raise InvalidParameterValueException(
                "computeResources must be specified when creating a {0} environment".format(
                    state
                )
            )
        elif compute_resources is not None:
            self._validate_compute_resources(compute_resources)

        # By here, all values except SPOT ones have been validated
        new_comp_env = ComputeEnvironment(
            compute_environment_name,
            _type,
            state,
            compute_resources,
            service_role,
            region_name=self.region_name,
        )
        self._compute_environments[new_comp_env.arn] = new_comp_env

        # Ok by this point, everything is legit, so if its Managed then start some instances
        if _type == "MANAGED" and "FARGATE" not in compute_resources["type"]:
            cpus = int(
                compute_resources.get("desiredvCpus", compute_resources["minvCpus"])
            )
            instance_types = compute_resources["instanceTypes"]
            needed_instance_types = self.find_min_instances_to_meet_vcpus(
                instance_types, cpus
            )
            # Create instances

            # Will loop over and over so we get decent subnet coverage
            subnet_cycle = cycle(compute_resources["subnets"])

            for instance_type in needed_instance_types:
                reservation = self.ec2_backend.add_instances(
                    image_id="ami-03cf127a",  # Todo import AMIs
                    count=1,
                    user_data=None,
                    security_group_names=[],
                    instance_type=instance_type,
                    region_name=self.region_name,
                    subnet_id=next(subnet_cycle),
                    key_name=compute_resources.get("ec2KeyPair", "AWS_OWNED"),
                    security_group_ids=compute_resources["securityGroupIds"],
                    is_instance_type_default=False,
                )

                new_comp_env.add_instance(reservation.instances[0])

        # Create ECS cluster
        # Should be of format P2OnDemand_Batch_UUID
        cluster_name = "OnDemand_Batch_" + str(uuid.uuid4())
        ecs_cluster = self.ecs_backend.create_cluster(cluster_name)
        new_comp_env.set_ecs(ecs_cluster.arn, cluster_name)

        return compute_environment_name, new_comp_env.arn

    def _validate_compute_resources(self, cr):
        """
        Checks contents of sub dictionary for managed clusters

        :param cr: computeResources
        :type cr: dict
        """
        if int(cr["maxvCpus"]) < 0:
            raise InvalidParameterValueException("maxVCpus must be positive")
        if "FARGATE" not in cr["type"]:
            # Most parameters are not applicable to jobs that are running on Fargate resources:
            # non exhaustive list: minvCpus, instanceTypes, imageId, ec2KeyPair, instanceRole, tags
            for profile in self.iam_backend.get_instance_profiles():
                if profile.arn == cr["instanceRole"]:
                    break
            else:
                raise InvalidParameterValueException(
                    "could not find instanceRole {0}".format(cr["instanceRole"])
                )

            if int(cr["minvCpus"]) < 0:
                raise InvalidParameterValueException("minvCpus must be positive")
            if int(cr["maxvCpus"]) < int(cr["minvCpus"]):
                raise InvalidParameterValueException(
                    "maxVCpus must be greater than minvCpus"
                )

            if len(cr["instanceTypes"]) == 0:
                raise InvalidParameterValueException(
                    "At least 1 instance type must be provided"
                )
            for instance_type in cr["instanceTypes"]:
                if instance_type == "optimal":
                    pass  # Optimal should pick from latest of current gen
                elif (
                    instance_type not in EC2_INSTANCE_TYPES
                    and instance_type not in EC2_INSTANCE_FAMILIES
                ):
                    raise InvalidParameterValueException(
                        "Instance type {0} does not exist".format(instance_type)
                    )

        for sec_id in cr["securityGroupIds"]:
            if self.ec2_backend.get_security_group_from_id(sec_id) is None:
                raise InvalidParameterValueException(
                    "security group {0} does not exist".format(sec_id)
                )
        if len(cr["securityGroupIds"]) == 0:
            raise InvalidParameterValueException(
                "At least 1 security group must be provided"
            )

        for subnet_id in cr["subnets"]:
            try:
                self.ec2_backend.get_subnet(subnet_id)
            except InvalidSubnetIdError:
                raise InvalidParameterValueException(
                    "subnet {0} does not exist".format(subnet_id)
                )
        if len(cr["subnets"]) == 0:
            raise InvalidParameterValueException("At least 1 subnet must be provided")

        if cr["type"] not in {"EC2", "SPOT", "FARGATE", "FARGATE_SPOT"}:
            raise InvalidParameterValueException(
                "computeResources.type must be either EC2 | SPOT | FARGATE | FARGATE_SPOT"
            )

    @staticmethod
    def find_min_instances_to_meet_vcpus(instance_types, target):
        """
        Finds the minimum needed instances to meed a vcpu target

        :param instance_types: Instance types, like ['t2.medium', 't2.small']
        :type instance_types: list of str
        :param target: VCPU target
        :type target: float
        :return: List of instance types
        :rtype: list of str
        """
        # vcpus = [ (vcpus, instance_type), (vcpus, instance_type), ... ]
        instance_vcpus = []
        instances = []

        for instance_type in instance_types:
            if instance_type == "optimal":
                instance_type = "m4.4xlarge"

            if "." not in instance_type:
                # instance_type can be a family of instance types (c2, t3, etc)
                # We'll just use the first instance_type in this family
                instance_type = [
                    i for i in EC2_INSTANCE_TYPES.keys() if i.startswith(instance_type)
                ][0]
            instance_vcpus.append(
                (
                    EC2_INSTANCE_TYPES[instance_type]["VCpuInfo"]["DefaultVCpus"],
                    instance_type,
                )
            )

        instance_vcpus = sorted(instance_vcpus, key=lambda item: item[0], reverse=True)
        # Loop through,
        #   if biggest instance type smaller than target, and len(instance_types)> 1, then use biggest type
        #   if biggest instance type bigger than target, and len(instance_types)> 1, then remove it and move on

        #   if biggest instance type bigger than target and len(instan_types) == 1 then add instance and finish
        #   if biggest instance type smaller than target and len(instan_types) == 1 then loop adding instances until target == 0
        #   ^^ boils down to keep adding last till target vcpus is negative
        #   #Algorithm ;-) ... Could probably be done better with some quality lambdas
        while target > 0:
            current_vcpu, current_instance = instance_vcpus[0]

            if len(instance_vcpus) > 1:
                if current_vcpu <= target:
                    target -= current_vcpu
                    instances.append(current_instance)
                else:
                    # try next biggest instance
                    instance_vcpus.pop(0)
            else:
                # Were on the last instance
                target -= current_vcpu
                instances.append(current_instance)

        return instances

    def delete_compute_environment(self, compute_environment_name):
        if compute_environment_name is None:
            raise InvalidParameterValueException("Missing computeEnvironment parameter")

        compute_env = self.get_compute_environment(compute_environment_name)

        if compute_env is not None:
            # Pop ComputeEnvironment
            self._compute_environments.pop(compute_env.arn)

            # Delete ECS cluster
            self.ecs_backend.delete_cluster(compute_env.ecs_name)

            if compute_env.env_type == "MANAGED":
                # Delete compute environment
                instance_ids = [instance.id for instance in compute_env.instances]
                if instance_ids:
                    self.ec2_backend.terminate_instances(instance_ids)

    def update_compute_environment(
        self, compute_environment_name, state, compute_resources, service_role
    ):
        # Validate
        compute_env = self.get_compute_environment(compute_environment_name)
        if compute_env is None:
            raise ClientException("Compute environment {0} does not exist")

        # Look for IAM role
        if service_role is not None:
            try:
                role = self.iam_backend.get_role_by_arn(service_role)
            except IAMNotFoundException:
                raise InvalidParameterValueException(
                    "Could not find IAM role {0}".format(service_role)
                )

            compute_env.service_role = role

        if state is not None:
            if state not in ("ENABLED", "DISABLED"):
                raise InvalidParameterValueException(
                    "state {0} must be one of ENABLED | DISABLED".format(state)
                )

            compute_env.state = state

        if compute_resources is not None:
            # TODO Implement resizing of instances based on changing vCpus
            # compute_resources CAN contain desiredvCpus, maxvCpus, minvCpus, and can contain none of them.
            pass

        return compute_env.name, compute_env.arn

    def create_job_queue(
        self, queue_name, priority, state, compute_env_order, tags=None
    ):
        for variable, var_name in (
            (queue_name, "jobQueueName"),
            (priority, "priority"),
            (state, "state"),
            (compute_env_order, "computeEnvironmentOrder"),
        ):
            if variable is None:
                raise ClientException("{0} must be provided".format(var_name))

        if state not in ("ENABLED", "DISABLED"):
            raise ClientException(
                "state {0} must be one of ENABLED | DISABLED".format(state)
            )
        if self.get_job_queue_by_name(queue_name) is not None:
            raise ClientException("Job queue {0} already exists".format(queue_name))

        if len(compute_env_order) == 0:
            raise ClientException("At least 1 compute environment must be provided")
        try:
            # orders and extracts computeEnvironment names
            ordered_compute_environments = [
                item["computeEnvironment"]
                for item in sorted(compute_env_order, key=lambda x: x["order"])
            ]
            env_objects = []
            # Check each ARN exists, then make a list of compute env's
            for arn in ordered_compute_environments:
                env = self.get_compute_environment_by_arn(arn)
                if env is None:
                    raise ClientException(
                        "Compute environment {0} does not exist".format(arn)
                    )
                env_objects.append(env)
        except Exception:
            raise ClientException("computeEnvironmentOrder is malformed")

        # Create new Job Queue
        queue = JobQueue(
            queue_name,
            priority,
            state,
            env_objects,
            compute_env_order,
            self.region_name,
            backend=self,
            tags=tags,
        )
        self._job_queues[queue.arn] = queue

        return queue_name, queue.arn

    def describe_job_queues(self, job_queues=None):
        """
        Pagination is not yet implemented
        """
        envs = set()
        if job_queues is not None:
            envs = set(job_queues)

        result = []
        for arn, job_queue in self._job_queues.items():
            # Filter shortcut
            if len(envs) > 0 and arn not in envs and job_queue.name not in envs:
                continue

            result.append(job_queue.describe())

        return result

    def update_job_queue(self, queue_name, priority, state, compute_env_order):
        if queue_name is None:
            raise ClientException("jobQueueName must be provided")

        job_queue = self.get_job_queue(queue_name)
        if job_queue is None:
            raise ClientException("Job queue {0} does not exist".format(queue_name))

        if state is not None:
            if state not in ("ENABLED", "DISABLED"):
                raise ClientException(
                    "state {0} must be one of ENABLED | DISABLED".format(state)
                )

            job_queue.state = state

        if compute_env_order is not None:
            if len(compute_env_order) == 0:
                raise ClientException("At least 1 compute environment must be provided")
            try:
                # orders and extracts computeEnvironment names
                ordered_compute_environments = [
                    item["computeEnvironment"]
                    for item in sorted(compute_env_order, key=lambda x: x["order"])
                ]
                env_objects = []
                # Check each ARN exists, then make a list of compute env's
                for arn in ordered_compute_environments:
                    env = self.get_compute_environment_by_arn(arn)
                    if env is None:
                        raise ClientException(
                            "Compute environment {0} does not exist".format(arn)
                        )
                    env_objects.append(env)
            except Exception:
                raise ClientException("computeEnvironmentOrder is malformed")

            job_queue.env_order_json = compute_env_order
            job_queue.environments = env_objects

        if priority is not None:
            job_queue.priority = priority

        return queue_name, job_queue.arn

    def delete_job_queue(self, queue_name):
        job_queue = self.get_job_queue(queue_name)

        if job_queue is not None:
            del self._job_queues[job_queue.arn]

    def register_job_definition(
        self,
        def_name,
        parameters,
        _type,
        tags,
        retry_strategy,
        container_properties,
        timeout,
        platform_capabilities,
        propagate_tags,
    ):
        if def_name is None:
            raise ClientException("jobDefinitionName must be provided")

        job_def = self.get_job_definition_by_name(def_name)
        if retry_strategy is not None and "evaluateOnExit" in retry_strategy:
            for strat in retry_strategy["evaluateOnExit"]:
                if "action" in strat:
                    strat["action"] = strat["action"].lower()
        if not tags:
            tags = {}
        if job_def is None:
            job_def = JobDefinition(
                def_name,
                parameters,
                _type,
                container_properties,
                tags=tags,
                region_name=self.region_name,
                retry_strategy=retry_strategy,
                timeout=timeout,
                backend=self,
                platform_capabilities=platform_capabilities,
                propagate_tags=propagate_tags,
            )
        else:
            # Make new jobdef
            job_def = job_def.update(
                parameters, _type, container_properties, retry_strategy, tags, timeout
            )

        self._job_definitions[job_def.arn] = job_def

        return def_name, job_def.arn, job_def.revision

    def deregister_job_definition(self, def_name):
        job_def = self.get_job_definition_by_arn(def_name)
        if job_def is None and ":" in def_name:
            name, revision = def_name.split(":", 1)
            job_def = self.get_job_definition_by_name_revision(name, revision)

        if job_def is not None:
            self._job_definitions[job_def.arn].deregister()

    def describe_job_definitions(
        self, job_def_name=None, job_def_list=None, status=None
    ):
        """
        Pagination is not yet implemented
        """
        jobs = []

        # As a job name can reference multiple revisions, we get a list of them
        if job_def_name is not None:
            job_def = self.get_job_definitions(job_def_name)
            if job_def is not None:
                jobs.extend(job_def)
        elif job_def_list is not None:
            for job in job_def_list:
                job_def = self.get_job_definitions(job)
                if job_def is not None:
                    jobs.extend(job_def)
        else:
            jobs.extend(self._job_definitions.values())

        # Got all the job defs were after, filter then by status
        if status is not None:
            return [job for job in jobs if job.status == status]
        for job in jobs:
            job.describe()
        return jobs

    def submit_job(
        self,
        job_name,
        job_def_id,
        job_queue,
        depends_on=None,
        container_overrides=None,
        timeout=None,
    ):
        """
        Parameters RetryStrategy and Parameters are not yet implemented.
        """
        # Look for job definition
        job_def = self.get_job_definition(job_def_id)
        if job_def is None:
            raise ClientException(
                "Job definition {0} does not exist".format(job_def_id)
            )

        queue = self.get_job_queue(job_queue)
        if queue is None:
            raise ClientException("Job queue {0} does not exist".format(job_queue))

        job = Job(
            job_name,
            job_def,
            queue,
            log_backend=self.logs_backend,
            container_overrides=container_overrides,
            depends_on=depends_on,
            all_jobs=self._jobs,
            timeout=timeout,
        )
        self._jobs[job.job_id] = job

        # Here comes the fun
        job.start()

        return job_name, job.job_id

    def describe_jobs(self, jobs):
        job_filter = set()
        if jobs is not None:
            job_filter = set(jobs)

        result = []
        for key, job in self._jobs.items():
            if len(job_filter) > 0 and key not in job_filter:
                continue

            result.append(job.describe())

        return result

    def list_jobs(self, job_queue, job_status=None):
        """
        Pagination is not yet implemented
        """
        jobs = []

        job_queue = self.get_job_queue(job_queue)
        if job_queue is None:
            raise ClientException("Job queue {0} does not exist".format(job_queue))

        if job_status is not None and job_status not in (
            "SUBMITTED",
            "PENDING",
            "RUNNABLE",
            "STARTING",
            "RUNNING",
            "SUCCEEDED",
            "FAILED",
        ):
            raise ClientException(
                "Job status is not one of SUBMITTED | PENDING | RUNNABLE | STARTING | RUNNING | SUCCEEDED | FAILED"
            )

        for job in job_queue.jobs:
            if job_status is not None and job.status != job_status:
                continue

            jobs.append(job)

        return jobs

    def cancel_job(self, job_id, reason):
        job = self.get_job_by_id(job_id)
        if job.status in ["SUBMITTED", "PENDING", "RUNNABLE"]:
            job.terminate(reason)
        # No-Op for jobs that have already started - user has to explicitly terminate those

    def terminate_job(self, job_id, reason):
        if job_id is None:
            raise ClientException("Job ID does not exist")
        if reason is None:
            raise ClientException("Reason does not exist")

        job = self.get_job_by_id(job_id)
        if job is None:
            raise ClientException("Job not found")

        job.terminate(reason)

    def tag_resource(self, resource_arn, tags):
        tags = self.tagger.convert_dict_to_tags_input(tags or {})
        self.tagger.tag_resource(resource_arn, tags)

    def list_tags_for_resource(self, resource_arn):
        return self.tagger.get_tag_dict_for_resource(resource_arn)

    def untag_resource(self, resource_arn, tag_keys):
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)


batch_backends = BackendDict(BatchBackend, "batch")
