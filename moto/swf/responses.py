import json
import logging
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

    # TODO: implement pagination
    def list_domains(self):
        status = self._params.get("registrationStatus")
        reverse_order = self._params.get("reverseOrder", None)
        domains = self.swf_backend.list_domains(status, reverse_order=reverse_order)
        template = self.response_template(LIST_DOMAINS_TEMPLATE)
        return template.render(domains=domains)

    def register_domain(self):
        name = self._params.get("name")
        description = self._params.get("description")
        retention = self._params.get("workflowExecutionRetentionPeriodInDays")
        domain = self.swf_backend.register_domain(name, retention,
                                                  description=description)
        template = self.response_template("")
        return template.render()

    def deprecate_domain(self):
        name = self._params.get("name")
        domain = self.swf_backend.deprecate_domain(name)
        template = self.response_template("")
        return template.render()

    def describe_domain(self):
        name = self._params.get("name")
        domain = self.swf_backend.describe_domain(name)
        template = self.response_template(DESCRIBE_DOMAIN_TEMPLATE)
        return template.render(domain=domain)

    # TODO: implement pagination
    def list_activity_types(self):
        domain_name = self._params.get("domain")
        status = self._params.get("registrationStatus")
        reverse_order = self._params.get("reverseOrder", None)
        actypes = self.swf_backend.list_activity_types(domain_name, status, reverse_order=reverse_order)
        template = self.response_template(LIST_ACTIVITY_TYPES_TEMPLATE)
        return template.render(actypes=actypes)

    def register_activity_type(self):
        domain = self._params.get("domain")
        name = self._params.get("name")
        version = self._params.get("version")
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
        activity_type = self.swf_backend.register_activity_type(
            domain, name, version, task_list=task_list,
            default_task_heartbeat_timeout=default_task_heartbeat_timeout,
            default_task_schedule_to_close_timeout=default_task_schedule_to_close_timeout,
            default_task_schedule_to_start_timeout=default_task_schedule_to_start_timeout,
            default_task_start_to_close_timeout=default_task_start_to_close_timeout,
            description=description,
        )
        template = self.response_template("")
        return template.render()

    def deprecate_activity_type(self):
        domain = self._params.get("domain")
        actype = self._params.get("activityType")
        name = actype["name"]
        version = actype["version"]
        domain = self.swf_backend.deprecate_activity_type(domain, name, version)
        template = self.response_template("")
        return template.render()

    def describe_activity_type(self):
        domain = self._params.get("domain")
        actype = self._params.get("activityType")

        name = actype["name"]
        version = actype["version"]
        actype = self.swf_backend.describe_activity_type(domain, name, version)
        template = self.response_template(DESCRIBE_ACTIVITY_TYPE_TEMPLATE)
        return template.render(actype=actype)


LIST_DOMAINS_TEMPLATE = """{
    "domainInfos": [
        {%- for domain in domains %}
        {
            "description": "{{ domain.description }}",
            "name": "{{ domain.name }}",
            "status": "{{ domain.status }}"
        }{% if not loop.last %},{% endif %}
        {%- endfor %}
    ]
}"""

DESCRIBE_DOMAIN_TEMPLATE = """{
    "configuration": {
        "workflowExecutionRetentionPeriodInDays": "{{ domain.retention }}"
    },
    "domainInfo": {
        "description": "{{ domain.description }}",
        "name": "{{ domain.name }}",
        "status": "{{ domain.status }}"
    }
}"""

LIST_ACTIVITY_TYPES_TEMPLATE = """{
    "typeInfos": [
        {%- for actype in actypes %}
        {
            "activityType": {
                "name": "{{ actype.name }}",
                "version": "{{ actype.version }}"
            },
            "creationDate": 1420066800,
            {% if actype.status == "DEPRECATED" %}"deprecationDate": 1422745200,{% endif %}
            {% if actype.description %}"description": "{{ actype.description }}",{% endif %}
            "status": "{{ actype.status }}"
        }{% if not loop.last %},{% endif %}
        {%- endfor %}
    ]
}"""

DESCRIBE_ACTIVITY_TYPE_TEMPLATE = """{
   "configuration": {
        {% if actype.default_task_heartbeat_timeout %}"defaultTaskHeartbeatTimeout": "{{ actype.default_task_heartbeat_timeout }}",{% endif %}
        {% if actype.task_list %}"defaultTaskList": { "name": "{{ actype.task_list }}" },{% endif %}
        {% if actype.default_task_schedule_to_close_timeout %}"defaultTaskScheduleToCloseTimeout": "{{ actype.default_task_schedule_to_close_timeout }}",{% endif %}
        {% if actype.default_task_schedule_to_start_timeout %}"defaultTaskScheduleToStartTimeout": "{{ actype.default_task_schedule_to_start_timeout }}",{% endif %}
        {% if actype.default_task_start_to_close_timeout %}"defaultTaskStartToCloseTimeout": "{{ actype.default_task_start_to_close_timeout }}",{% endif %}
        "__moto_placeholder": "(avoid dealing with coma in json)"
    },
    "typeInfo": {
        "activityType": {
            "name": "{{ actype.name }}",
            "version": "{{ actype.version }}"
        },
        "creationDate": 1420066800,
        {% if actype.status == "DEPRECATED" %}"deprecationDate": 1422745200,{% endif %}
        {% if actype.description %}"description": "{{ actype.description }}",{% endif %}
        "status": "{{ actype.status }}"
    }
}"""

