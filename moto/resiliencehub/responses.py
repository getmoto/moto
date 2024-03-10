import json
from typing import Any
from urllib.parse import unquote

from moto.core.responses import BaseResponse

from .exceptions import ValidationException
from .models import ResilienceHubBackend, resiliencehub_backends


class ResilienceHubResponse(BaseResponse):
    def tags(self, request: Any, full_url: str, headers: Any) -> str:  # type: ignore[return]
        self.setup_class(request, full_url, headers)
        if request.method == "GET":
            return self.list_tags_for_resource()
        if request.method == "POST":
            return self.tag_resource()
        if request.method == "DELETE":
            return self.untag_resource()

    def __init__(self) -> None:
        super().__init__(service_name="resiliencehub")

    @property
    def resiliencehub_backend(self) -> ResilienceHubBackend:
        return resiliencehub_backends[self.current_account][self.region]

    def create_app(self) -> str:
        params = json.loads(self.body)
        assessment_schedule = params.get("assessmentSchedule")
        description = params.get("description")
        event_subscriptions = params.get("eventSubscriptions")
        name = params.get("name")
        permission_model = params.get("permissionModel")
        policy_arn = params.get("policyArn")
        tags = params.get("tags")
        app = self.resiliencehub_backend.create_app(
            assessment_schedule=assessment_schedule,
            description=description,
            event_subscriptions=event_subscriptions,
            name=name,
            permission_model=permission_model,
            policy_arn=policy_arn,
            tags=tags,
        )
        return json.dumps(dict(app=app.to_json()))

    def create_resiliency_policy(self) -> str:
        params = json.loads(self.body)
        data_location_constraint = params.get("dataLocationConstraint")
        policy = params.get("policy")
        policy_description = params.get("policyDescription")
        policy_name = params.get("policyName")
        tags = params.get("tags")
        tier = params.get("tier")

        required_policy_types = ["Software", "Hardware", "AZ"]
        all_policy_types = required_policy_types + ["Region"]
        if any((p_type not in all_policy_types for p_type in policy.keys())):
            raise ValidationException(
                "1 validation error detected: Value at 'policy' failed to satisfy constraint: Map keys must satisfy constraint: [Member must satisfy enum value set: [Software, Hardware, Region, AZ]]"
            )
        for required_key in required_policy_types:
            if required_key not in policy.keys():
                raise ValidationException(
                    f"FailureType {required_key.upper()} does not exist"
                )

        policy = self.resiliencehub_backend.create_resiliency_policy(
            data_location_constraint=data_location_constraint,
            policy=policy,
            policy_description=policy_description,
            policy_name=policy_name,
            tags=tags,
            tier=tier,
        )
        return json.dumps(dict(policy=policy.to_json()))

    def list_apps(self) -> str:
        params = self._get_params()
        app_arn = params.get("appArn")
        max_results = int(params.get("maxResults", 100))
        name = params.get("name")
        next_token = params.get("nextToken")
        reverse_order = params.get("reverseOrder") == "true"
        app_summaries, next_token = self.resiliencehub_backend.list_apps(
            app_arn=app_arn,
            max_results=max_results,
            name=name,
            next_token=next_token,
            reverse_order=reverse_order,
        )
        return json.dumps(
            dict(
                appSummaries=[a.to_json() for a in app_summaries], nextToken=next_token
            )
        )

    def list_app_assessments(self) -> str:
        summaries = self.resiliencehub_backend.list_app_assessments()
        return json.dumps(dict(assessmentSummaries=summaries))

    def describe_app(self) -> str:
        params = json.loads(self.body)
        app_arn = params.get("appArn")
        app = self.resiliencehub_backend.describe_app(
            app_arn=app_arn,
        )
        return json.dumps(dict(app=app.to_json()))

    def list_resiliency_policies(self) -> str:
        params = self._get_params()
        max_results = int(params.get("maxResults", 100))
        next_token = params.get("nextToken")
        policy_name = params.get("policyName")
        (
            resiliency_policies,
            next_token,
        ) = self.resiliencehub_backend.list_resiliency_policies(
            max_results=max_results,
            next_token=next_token,
            policy_name=policy_name,
        )
        policies = [p.to_json() for p in resiliency_policies]
        return json.dumps(dict(nextToken=next_token, resiliencyPolicies=policies))

    def describe_resiliency_policy(self) -> str:
        params = json.loads(self.body)
        policy_arn = params.get("policyArn")
        policy = self.resiliencehub_backend.describe_resiliency_policy(
            policy_arn=policy_arn,
        )
        return json.dumps(dict(policy=policy.to_json()))

    def tag_resource(self) -> str:
        params = json.loads(self.body)
        resource_arn = unquote(self.parsed_url.path.split("/tags/")[-1])
        tags = params.get("tags")
        self.resiliencehub_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        return "{}"

    def untag_resource(self) -> str:
        resource_arn = unquote(self.parsed_url.path.split("/tags/")[-1])
        tag_keys = self.querystring.get("tagKeys", [])
        self.resiliencehub_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        return "{}"

    def list_tags_for_resource(self) -> str:
        resource_arn = unquote(self.uri.split("/tags/")[-1])
        tags = self.resiliencehub_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        return json.dumps(dict(tags=tags))
