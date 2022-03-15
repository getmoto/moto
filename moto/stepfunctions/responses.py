import json

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .models import stepfunction_backends


class StepFunctionResponse(BaseResponse):
    @property
    def stepfunction_backend(self):
        return stepfunction_backends[self.region]

    @amzn_request_id
    def create_state_machine(self):
        name = self._get_param("name")
        definition = self._get_param("definition")
        roleArn = self._get_param("roleArn")
        tags = self._get_param("tags")
        state_machine = self.stepfunction_backend.create_state_machine(
            name=name, definition=definition, roleArn=roleArn, tags=tags
        )
        response = {
            "creationDate": state_machine.creation_date,
            "stateMachineArn": state_machine.arn,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_state_machines(self):
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        results, next_token = self.stepfunction_backend.list_state_machines(
            max_results=max_results, next_token=next_token
        )
        state_machines = [
            {
                "creationDate": sm.creation_date,
                "name": sm.name,
                "stateMachineArn": sm.arn,
            }
            for sm in results
        ]
        response = {"stateMachines": state_machines}
        if next_token:
            response["nextToken"] = next_token
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_state_machine(self):
        arn = self._get_param("stateMachineArn")
        return self._describe_state_machine(arn)

    @amzn_request_id
    def _describe_state_machine(self, state_machine_arn):
        state_machine = self.stepfunction_backend.describe_state_machine(
            state_machine_arn
        )
        response = {
            "creationDate": state_machine.creation_date,
            "stateMachineArn": state_machine.arn,
            "definition": state_machine.definition,
            "name": state_machine.name,
            "roleArn": state_machine.roleArn,
            "status": "ACTIVE",
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def delete_state_machine(self):
        arn = self._get_param("stateMachineArn")
        self.stepfunction_backend.delete_state_machine(arn)
        return 200, {}, json.dumps("{}")

    @amzn_request_id
    def update_state_machine(self):
        arn = self._get_param("stateMachineArn")
        definition = self._get_param("definition")
        role_arn = self._get_param("roleArn")
        state_machine = self.stepfunction_backend.update_state_machine(
            arn=arn, definition=definition, role_arn=role_arn
        )
        response = {
            "updateDate": state_machine.update_date,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_tags_for_resource(self):
        arn = self._get_param("resourceArn")
        tags = self.stepfunction_backend.list_tags_for_resource(arn)
        response = {"tags": tags}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def tag_resource(self):
        arn = self._get_param("resourceArn")
        tags = self._get_param("tags", [])
        self.stepfunction_backend.tag_resource(arn, tags)
        return 200, {}, json.dumps({})

    @amzn_request_id
    def untag_resource(self):
        arn = self._get_param("resourceArn")
        tag_keys = self._get_param("tagKeys", [])
        self.stepfunction_backend.untag_resource(arn, tag_keys)
        return 200, {}, json.dumps({})

    @amzn_request_id
    def start_execution(self):
        arn = self._get_param("stateMachineArn")
        name = self._get_param("name")
        execution_input = self._get_param("input", if_none="{}")
        execution = self.stepfunction_backend.start_execution(
            arn, name, execution_input
        )
        response = {
            "executionArn": execution.execution_arn,
            "startDate": execution.start_date,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def list_executions(self):
        max_results = self._get_int_param("maxResults")
        next_token = self._get_param("nextToken")
        arn = self._get_param("stateMachineArn")
        status_filter = self._get_param("statusFilter")
        state_machine = self.stepfunction_backend.describe_state_machine(arn)
        results, next_token = self.stepfunction_backend.list_executions(
            arn,
            status_filter=status_filter,
            max_results=max_results,
            next_token=next_token,
        )
        executions = [
            {
                "executionArn": execution.execution_arn,
                "name": execution.name,
                "startDate": execution.start_date,
                "stateMachineArn": state_machine.arn,
                "status": execution.status,
            }
            for execution in results
        ]
        response = {"executions": executions}
        if next_token:
            response["nextToken"] = next_token
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_execution(self):
        arn = self._get_param("executionArn")
        execution = self.stepfunction_backend.describe_execution(arn)
        response = {
            "executionArn": arn,
            "input": execution.execution_input,
            "name": execution.name,
            "startDate": execution.start_date,
            "stateMachineArn": execution.state_machine_arn,
            "status": execution.status,
            "stopDate": execution.stop_date,
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_state_machine_for_execution(self):
        arn = self._get_param("executionArn")
        execution = self.stepfunction_backend.describe_execution(arn)
        return self._describe_state_machine(execution.state_machine_arn)

    @amzn_request_id
    def stop_execution(self):
        arn = self._get_param("executionArn")
        execution = self.stepfunction_backend.stop_execution(arn)
        response = {"stopDate": execution.stop_date}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def get_execution_history(self):
        execution_arn = self._get_param("executionArn")
        execution_history = self.stepfunction_backend.get_execution_history(
            execution_arn
        )
        response = {"events": execution_history}
        return 200, {}, json.dumps(response)
