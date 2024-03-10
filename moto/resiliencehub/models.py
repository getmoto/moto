from typing import Any, Dict, List

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService

from .exceptions import AppNotFound, ResiliencyPolicyNotFound

PAGINATION_MODEL = {
    "list_apps": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "unique_attribute": "arn",
    },
    "list_resiliency_policies": {
        "input_token": "next_token",
        "limit_key": "max_results",
        "limit_default": 100,
        "unique_attribute": "arn",
    },
}


class App(BaseModel):
    def __init__(
        self,
        backend: "ResilienceHubBackend",
        assessment_schedule: str,
        description: str,
        event_subscriptions: List[Dict[str, Any]],
        name: str,
        permission_model: Dict[str, Any],
        policy_arn: str,
    ):
        self.backend = backend
        self.arn = f"arn:aws:resiliencehub:{backend.region_name}:{backend.account_id}:app/{mock_random.uuid4()}"
        self.assessment_schedule = assessment_schedule or "Disabled"
        self.compliance_status = "NotAssessed"
        self.description = description
        self.creation_time = unix_time()
        self.event_subscriptions = event_subscriptions
        self.name = name
        self.permission_model = permission_model
        self.policy_arn = policy_arn
        self.resilience_score = 0.0
        self.status = "Active"

    def to_json(self) -> Dict[str, Any]:
        resp = {
            "appArn": self.arn,
            "assessmentSchedule": self.assessment_schedule,
            "complianceStatus": self.compliance_status,
            "creationTime": self.creation_time,
            "name": self.name,
            "resilienceScore": self.resilience_score,
            "status": self.status,
            "tags": self.backend.list_tags_for_resource(self.arn),
        }
        if self.description is not None:
            resp["description"] = self.description
        if self.event_subscriptions:
            resp["eventSubscriptions"] = self.event_subscriptions
        if self.permission_model:
            resp["permissionModel"] = self.permission_model
        if self.policy_arn:
            resp["policyArn"] = self.policy_arn
        return resp


class Policy(BaseModel):
    def __init__(
        self,
        backend: "ResilienceHubBackend",
        policy: Dict[str, Dict[str, int]],
        policy_name: str,
        data_location_constraint: str,
        policy_description: str,
        tier: str,
    ):
        self.arn = f"arn:aws:resiliencehub:{backend.region_name}:{backend.account_id}:resiliency-policy/{mock_random.uuid4()}"
        self.backend = backend
        self.data_location_constraint = data_location_constraint
        self.creation_time = unix_time()
        self.policy = policy
        self.policy_description = policy_description
        self.policy_name = policy_name
        self.tier = tier

    def to_json(self) -> Dict[str, Any]:
        resp = {
            "creationTime": self.creation_time,
            "policy": self.policy,
            "policyArn": self.arn,
            "policyName": self.policy_name,
            "tags": self.backend.list_tags_for_resource(self.arn),
            "tier": self.tier,
        }
        if self.data_location_constraint:
            resp["dataLocationConstraint"] = self.data_location_constraint
        if self.policy_description:
            resp["policyDescription"] = self.policy_description
        return resp


class ResilienceHubBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.apps: Dict[str, App] = dict()
        self.policies: Dict[str, Policy] = dict()
        self.tagger = TaggingService()

    def create_app(
        self,
        assessment_schedule: str,
        description: str,
        event_subscriptions: List[Dict[str, Any]],
        name: str,
        permission_model: Dict[str, Any],
        policy_arn: str,
        tags: Dict[str, str],
    ) -> App:
        """
        The ClientToken-parameter is not yet implemented
        """
        app = App(
            backend=self,
            assessment_schedule=assessment_schedule,
            description=description,
            event_subscriptions=event_subscriptions,
            name=name,
            permission_model=permission_model,
            policy_arn=policy_arn,
        )
        self.apps[app.arn] = app
        self.tag_resource(app.arn, tags)
        return app

    def create_resiliency_policy(
        self,
        data_location_constraint: str,
        policy: Dict[str, Any],
        policy_description: str,
        policy_name: str,
        tags: Dict[str, str],
        tier: str,
    ) -> Policy:
        """
        The ClientToken-parameter is not yet implemented
        """
        pol = Policy(
            backend=self,
            data_location_constraint=data_location_constraint,
            policy=policy,
            policy_description=policy_description,
            policy_name=policy_name,
            tier=tier,
        )
        self.policies[pol.arn] = pol
        self.tag_resource(pol.arn, tags)
        return pol

    @paginate(PAGINATION_MODEL)
    def list_apps(self, app_arn: str, name: str, reverse_order: bool) -> List[App]:
        """
        The FromAssessmentTime/ToAssessmentTime-parameters are not yet implemented
        """
        if name:
            app_summaries = [a for a in self.apps.values() if a.name == name]
        elif app_arn:
            app_summaries = [self.apps[app_arn]]
        else:
            app_summaries = list(self.apps.values())
        if reverse_order:
            app_summaries.reverse()
        return app_summaries

    def list_app_assessments(self) -> List[str]:
        return []

    def describe_app(self, app_arn: str) -> App:
        if app_arn not in self.apps:
            raise AppNotFound(app_arn)
        return self.apps[app_arn]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_resiliency_policies(self, policy_name: str) -> List[Policy]:
        if policy_name:
            return [p for p in self.policies.values() if p.policy_name == policy_name]
        return list(self.policies.values())

    def describe_resiliency_policy(self, policy_arn: str) -> Policy:
        if policy_arn not in self.policies:
            raise ResiliencyPolicyNotFound(policy_arn)
        return self.policies[policy_arn]

    def tag_resource(self, resource_arn: str, tags: Dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, TaggingService.convert_dict_to_tags_input(tags)
        )

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)

    def list_tags_for_resource(self, resource_arn: str) -> Dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)


resiliencehub_backends = BackendDict(ResilienceHubBackend, "resiliencehub")
