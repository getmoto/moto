import json
import six

from moto.core.responses import BaseResponse
from werkzeug.exceptions import HTTPException
from moto.core.utils import camelcase_to_underscores, method_names_from_class

from .models import swf_backends


class SWFResponse(BaseResponse):

    @property
    def swf_backend(self):
        return swf_backends[self.region]

    # SWF actions are not dispatched via URLs but via a specific header called
    # "x-amz-target", in the form of com.amazonaws.swf.service.model.SimpleWorkflowService.<action>
    # This is not supported directly in BaseResponse sor for now we override
    # the call_action() method
    # See: http://docs.aws.amazon.com/amazonswf/latest/developerguide/UsingJSON-swf.html
    def call_action(self):
        headers = self.response_headers
        # Headers are case-insensitive. Probably a better way to do this.
        match = self.headers.get('x-amz-target') or self.headers.get('X-Amz-Target')
        if match:
            # TODO: see if we can call "[-1]" in BaseResponse, which would
            # allow to remove that
            action = match.split(".")[-1]

        action = camelcase_to_underscores(action)
        method_names = method_names_from_class(self.__class__)
        if action in method_names:
            method = getattr(self, action)
            try:
                response = method()
            except HTTPException as http_error:
                response = http_error.description, dict(status=http_error.code)
            if isinstance(response, six.string_types):
                return 200, headers, response
            else:
                body, new_headers = response
                status = new_headers.get('status', 200)
                headers.update(new_headers)
                return status, headers, body
        raise NotImplementedError("The {0} action has not been implemented".format(action))

    # SWF parameters are passed through a JSON body, so let's ease retrieval
    @property
    def _params(self):
        return json.loads(self.body)

    def _list_types(self, kind):
        domain_name = self._params["domain"]
        status = self._params["registrationStatus"]
        reverse_order = self._params.get("reverseOrder", None)
        types = self.swf_backend.list_types(kind, domain_name, status, reverse_order=reverse_order)
        return json.dumps({
            "typeInfos": [_type.to_medium_dict() for _type in types]
        })

    def _describe_type(self, kind):
        domain = self._params["domain"]
        _type_args = self._params["{0}Type".format(kind)]
        name = _type_args["name"]
        version = _type_args["version"]
        _type = self.swf_backend.describe_type(kind, domain, name, version)

        return json.dumps(_type.to_full_dict())

    def _deprecate_type(self, kind):
        domain = self._params["domain"]
        _type_args = self._params["{0}Type".format(kind)]
        name = _type_args["name"]
        version = _type_args["version"]
        self.swf_backend.deprecate_type(kind, domain, name, version)
        return ""

    # TODO: implement pagination
    def list_domains(self):
        status = self._params["registrationStatus"]
        reverse_order = self._params.get("reverseOrder", None)
        domains = self.swf_backend.list_domains(status, reverse_order=reverse_order)
        return json.dumps({
            "domainInfos": [domain.to_short_dict() for domain in domains]
        })

    def register_domain(self):
        name = self._params["name"]
        retention = self._params["workflowExecutionRetentionPeriodInDays"]
        description = self._params.get("description")
        domain = self.swf_backend.register_domain(name, retention,
                                                  description=description)
        return ""

    def deprecate_domain(self):
        name = self._params["name"]
        domain = self.swf_backend.deprecate_domain(name)
        return ""

    def describe_domain(self):
        name = self._params["name"]
        domain = self.swf_backend.describe_domain(name)
        return json.dumps(domain.to_full_dict())

    # TODO: implement pagination
    def list_activity_types(self):
        return self._list_types("activity")

    def register_activity_type(self):
        domain = self._params["domain"]
        name = self._params["name"]
        version = self._params["version"]
        default_task_list = self._params.get("defaultTaskList")
        if default_task_list:
            task_list = default_task_list.get("name")
        else:
            task_list = None
        default_task_heartbeat_timeout = self._params.get("defaultTaskHeartbeatTimeout")
        default_task_schedule_to_close_timeout = self._params.get("defaultTaskScheduleToCloseTimeout")
        default_task_schedule_to_start_timeout = self._params.get("defaultTaskScheduleToStartTimeout")
        default_task_start_to_close_timeout = self._params.get("defaultTaskStartToCloseTimeout")
        description = self._params.get("description")
        # TODO: add defaultTaskPriority when boto gets to support it
        activity_type = self.swf_backend.register_type(
            "activity", domain, name, version, task_list=task_list,
            default_task_heartbeat_timeout=default_task_heartbeat_timeout,
            default_task_schedule_to_close_timeout=default_task_schedule_to_close_timeout,
            default_task_schedule_to_start_timeout=default_task_schedule_to_start_timeout,
            default_task_start_to_close_timeout=default_task_start_to_close_timeout,
            description=description,
        )
        return ""

    def deprecate_activity_type(self):
        return self._deprecate_type("activity")

    def describe_activity_type(self):
        return self._describe_type("activity")

    def list_workflow_types(self):
        return self._list_types("workflow")

    def register_workflow_type(self):
        domain = self._params["domain"]
        name = self._params["name"]
        version = self._params["version"]
        default_task_list = self._params.get("defaultTaskList")
        if default_task_list:
            task_list = default_task_list.get("name")
        else:
            task_list = None
        default_child_policy = self._params.get("defaultChildPolicy")
        default_task_start_to_close_timeout = self._params.get("defaultTaskStartToCloseTimeout")
        default_execution_start_to_close_timeout = self._params.get("defaultExecutionStartToCloseTimeout")
        description = self._params.get("description")
        # TODO: add defaultTaskPriority when boto gets to support it
        # TODO: add defaultLambdaRole when boto gets to support it
        workflow_type = self.swf_backend.register_type(
            "workflow", domain, name, version, task_list=task_list,
            default_child_policy=default_child_policy,
            default_task_start_to_close_timeout=default_task_start_to_close_timeout,
            default_execution_start_to_close_timeout=default_execution_start_to_close_timeout,
            description=description,
        )
        return ""

    def deprecate_workflow_type(self):
        return self._deprecate_type("workflow")

    def describe_workflow_type(self):
        return self._describe_type("workflow")

    def start_workflow_execution(self):
        domain = self._params["domain"]
        workflow_id = self._params["workflowId"]
        _workflow_type = self._params["workflowType"]
        workflow_name = _workflow_type["name"]
        workflow_version = _workflow_type["version"]
        _default_task_list = self._params.get("defaultTaskList")
        if _default_task_list:
            task_list = _default_task_list.get("name")
        else:
            task_list = None
        child_policy = self._params.get("childPolicy")
        execution_start_to_close_timeout = self._params.get("executionStartToCloseTimeout")
        input_ = self._params.get("input")
        tag_list = self._params.get("tagList")
        task_start_to_close_timeout = self._params.get("taskStartToCloseTimeout")

        wfe = self.swf_backend.start_workflow_execution(
            domain, workflow_id, workflow_name, workflow_version,
            task_list=task_list, child_policy=child_policy,
            execution_start_to_close_timeout=execution_start_to_close_timeout,
            input=input_, tag_list=tag_list,
            task_start_to_close_timeout=task_start_to_close_timeout
        )

        return json.dumps({
            "runId": wfe.run_id
        })

    def describe_workflow_execution(self):
        domain_name = self._params["domain"]
        _workflow_execution = self._params["execution"]
        run_id = _workflow_execution["runId"]
        workflow_id = _workflow_execution["workflowId"]

        wfe = self.swf_backend.describe_workflow_execution(domain_name, run_id, workflow_id)
        return json.dumps(wfe.to_full_dict())

    def get_workflow_execution_history(self):
        domain_name = self._params["domain"]
        _workflow_execution = self._params["execution"]
        run_id = _workflow_execution["runId"]
        workflow_id = _workflow_execution["workflowId"]
        reverse_order = self._params.get("reverseOrder", None)
        wfe = self.swf_backend.describe_workflow_execution(domain_name, run_id, workflow_id)
        events = wfe.events(reverse_order=reverse_order)
        return json.dumps({
            "events": [evt.to_dict() for evt in events]
        })

    def poll_for_decision_task(self):
        domain_name = self._params["domain"]
        task_list = self._params["taskList"]["name"]
        identity = self._params.get("identity")
        reverse_order = self._params.get("reverseOrder", None)
        decision = self.swf_backend.poll_for_decision_task(
            domain_name, task_list, identity=identity
        )
        if decision:
            return json.dumps(
                decision.to_full_dict(reverse_order=reverse_order)
            )
        else:
            return json.dumps({"previousStartedEventId": 0, "startedEventId": 0})

    def count_pending_decision_tasks(self):
        domain_name = self._params["domain"]
        task_list = self._params["taskList"]["name"]
        count = self.swf_backend.count_pending_decision_tasks(domain_name, task_list)
        return json.dumps({"count": count, "truncated": False})

    def respond_decision_task_completed(self):
        task_token = self._params["taskToken"]
        execution_context = self._params.get("executionContext")
        decisions = self._params.get("decisions")
        self.swf_backend.respond_decision_task_completed(
            task_token, decisions=decisions, execution_context=execution_context
        )
        return ""

    def poll_for_activity_task(self):
        domain_name = self._params["domain"]
        task_list = self._params["taskList"]["name"]
        identity = self._params.get("identity")
        activity_task = self.swf_backend.poll_for_activity_task(
            domain_name, task_list, identity=identity
        )
        if activity_task:
            return json.dumps(
                activity_task.to_full_dict()
            )
        else:
            return json.dumps({"startedEventId": 0})

    def count_pending_activity_tasks(self):
        domain_name = self._params["domain"]
        task_list = self._params["taskList"]["name"]
        count = self.swf_backend.count_pending_activity_tasks(domain_name, task_list)
        return json.dumps({"count": count, "truncated": False})

    def respond_activity_task_completed(self):
        task_token = self._params["taskToken"]
        result = self._params.get("result")
        self.swf_backend.respond_activity_task_completed(
            task_token, result=result
        )
        return ""

    def respond_activity_task_failed(self):
        task_token = self._params["taskToken"]
        reason = self._params.get("reason")
        details = self._params.get("details")
        self.swf_backend.respond_activity_task_failed(
            task_token, reason=reason, details=details
        )
        return ""

    def terminate_workflow_execution(self):
        domain_name = self._params["domain"]
        workflow_id = self._params["workflowId"]
        child_policy = self._params.get("childPolicy")
        details = self._params.get("details")
        reason = self._params.get("reason")
        run_id = self._params.get("runId")
        self.swf_backend.terminate_workflow_execution(
            domain_name, workflow_id, child_policy=child_policy,
            details=details, reason=reason, run_id=run_id
        )
        return ""

    def record_activity_task_heartbeat(self):
        task_token = self._params["taskToken"]
        details = self._params.get("details")
        self.swf_backend.record_activity_task_heartbeat(
            task_token, details=details
        )
        # TODO: make it dynamic when we implement activity tasks cancellation
        return json.dumps({"cancelRequested": False})
