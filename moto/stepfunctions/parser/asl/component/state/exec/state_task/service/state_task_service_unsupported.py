import logging
from typing import Set

from moto.stepfunctions.parser.asl.component.state.exec.state_task.credentials import (
    ComputedCredentials,
)
from moto.stepfunctions.parser.asl.component.state.exec.state_task.service.resource import (
    ResourceCondition,
    ResourceRuntimePart,
)
from moto.stepfunctions.parser.asl.component.state.exec.state_task.service.state_task_service_callback import (
    StateTaskServiceCallback,
)
from moto.stepfunctions.parser.asl.eval.environment import Environment
from moto.stepfunctions.parser.asl.utils.boto_client import boto_client_for

LOG = logging.getLogger(__name__)

_SUPPORTED_INTEGRATION_PATTERNS: Set[ResourceCondition] = {
    ResourceCondition.WaitForTaskToken,
}


class StateTaskServiceUnsupported(StateTaskServiceCallback):
    def __init__(self):
        super().__init__(supported_integration_patterns=_SUPPORTED_INTEGRATION_PATTERNS)

    def _log_unsupported_warning(self):
        # Logs that the optimised service integration is not supported,
        # however the request is being forwarded to the service.
        service_name = self._get_boto_service_name()
        resource_arn = self.resource.resource_arn
        LOG.warning(
            "Unsupported Optimised service integration for service_name '%s' in resource: '%s'. "
            "Attempting to forward request to service.",
            service_name,
            resource_arn,
        )

    def _eval_service_task(
        self,
        env: Environment,
        resource_runtime_part: ResourceRuntimePart,
        normalised_parameters: dict,
        task_credentials: ComputedCredentials,
    ):
        # Logs that the evaluation of this optimised service integration is not supported
        # and relays the call to the target service with the computed parameters.
        self._log_unsupported_warning()
        service_name = self._get_boto_service_name()
        boto_action = self._get_boto_service_action()
        boto_client = boto_client_for(
            region=resource_runtime_part.region,
            account=resource_runtime_part.account,
            service=service_name,
            credentials=task_credentials,
        )
        response = getattr(boto_client, boto_action)(**normalised_parameters)
        response.pop("ResponseMetadata", None)
        env.stack.append(response)
