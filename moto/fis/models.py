"""FISBackend class with methods for supported APIs."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.core.utils import unix_time
from moto.moto_api._internal import mock_random
from moto.moto_api._internal.managed_state_model import ManagedState
from moto.utilities.paginator import paginate
from moto.utilities.tagging_service import TaggingService
from moto.utilities.utils import get_partition

from .exceptions import ResourceNotFoundException


@dataclass
class TargetAccountConfiguration(BaseModel):
    account_id: str
    role_arn: str
    description: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        dct: dict[str, Any] = {
            "roleArn": self.role_arn,
            "accountId": self.account_id,
            "description": self.description,
        }
        return {k: v for k, v in dct.items() if v is not None}


@dataclass
class ResolvedTarget(BaseModel):
    resource_type: str
    target_name: str
    resource_arn: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "resourceType": self.resource_type,
            "targetName": self.target_name,
            "targetInformation": {"arn": self.resource_arn},
        }


@dataclass
class ExperimentTemplate(BaseModel):
    account_id: str
    region_name: str
    id: str
    client_token: str
    description: str
    stop_conditions: list[dict[str, Any]]
    targets: dict[str, Any]
    actions: dict[str, Any]
    role_arn: str
    log_configuration: Optional[dict[str, Any]]
    experiment_options: Optional[dict[str, Any]]
    experiment_report_configuration: Optional[dict[str, Any]]
    creation_time: float
    last_update_time: float
    target_account_configurations: dict[str, TargetAccountConfiguration] = field(
        default_factory=dict
    )

    @property
    def arn(self) -> str:
        return f"arn:{get_partition(self.region_name)}:fis:{self.region_name}:{self.account_id}:experiment-template/{self.id}"

    def to_dict(self, tags: Optional[dict[str, str]] = None) -> dict[str, Any]:
        dct: dict[str, Any] = {
            "id": self.id,
            "arn": self.arn,
            "description": self.description,
            "targets": self.targets or {},
            "actions": self.actions or {},
            "stopConditions": self.stop_conditions or [],
            "creationTime": self.creation_time,
            "lastUpdateTime": self.last_update_time,
            "roleArn": self.role_arn,
            "tags": tags or {},
            "logConfiguration": self.log_configuration,
            "experimentOptions": self.experiment_options,
            "targetAccountConfigurationsCount": len(self.target_account_configurations),
            "experimentReportConfiguration": self.experiment_report_configuration,
        }
        return {k: v for k, v in dct.items() if v is not None}

    def to_summary_dict(self, tags: Optional[dict[str, str]] = None) -> dict[str, Any]:
        return {
            "id": self.id,
            "arn": self.arn,
            "description": self.description,
            "creationTime": self.creation_time,
            "lastUpdateTime": self.last_update_time,
            "tags": tags or {},
        }


class Experiment(ManagedState, BaseModel):
    STATUS_REASONS: ClassVar[dict[str, str]] = {
        "pending": "Experiment is pending",
        "initiating": "Experiment is initiating",
        "running": "Experiment is running",
        "completed": "Experiment completed",
        "stopping": "Experiment is stopping",
        "stopped": "Experiment stopped",
    }
    # The experiment has finished; endTime is set and the state no longer moves.
    TERMINAL_STATUSES: ClassVar[list[str]] = ["completed", "stopped", "failed"]

    def __init__(
        self,
        account_id: str,
        region_name: str,
        id: str,
        client_token: str,
        experiment_template_id: str,
        role_arn: str,
        targets: dict[str, Any],
        actions: dict[str, Any],
        stop_conditions: list[dict[str, Any]],
        log_configuration: Optional[dict[str, Any]],
        experiment_options: dict[str, Any],
        experiment_report_configuration: Optional[dict[str, Any]],
        target_account_configurations: dict[str, TargetAccountConfiguration],
        creation_time: float,
        start_time: float,
    ):
        ManagedState.__init__(
            self,
            model_name="fis::experiment",
            transitions=[
                ("pending", "initiating"),
                ("initiating", "running"),
                ("running", "completed"),
                ("stopping", "stopped"),
            ],
        )
        self.account_id = account_id
        self.region_name = region_name
        self.id = id
        self.client_token = client_token
        self.experiment_template_id = experiment_template_id
        self.role_arn = role_arn
        self.targets = targets
        self.actions = actions
        self.stop_conditions = stop_conditions
        self.log_configuration = log_configuration
        self.experiment_options = experiment_options
        self.experiment_report_configuration = experiment_report_configuration
        # Taken from the experiment template when the experiment is started, so
        # that later changes to the template do not affect this experiment.
        self.target_account_configurations = target_account_configurations
        self.creation_time = creation_time
        self.start_time = start_time
        self.end_time: Optional[float] = None

    @property
    def arn(self) -> str:
        return f"arn:{get_partition(self.region_name)}:fis:{self.region_name}:{self.account_id}:experiment/{self.id}"

    def _sync_state(self) -> str:
        """Read the (possibly transitioned) status, and bring the experiment in line with it."""
        status = self.status or "pending"
        if status in self.TERMINAL_STATUSES and self.end_time is None:
            self.end_time = unix_time()
        # The actions of an experiment follow the experiment itself.
        for action in self.actions.values():
            if status in ("pending", "initiating"):
                continue
            if "startTime" not in action:
                action["startTime"] = self.start_time
            action["state"] = {
                "status": status,
                "reason": self.STATUS_REASONS.get(status, status),
            }
            if status in self.TERMINAL_STATUSES:
                action["endTime"] = self.end_time
        return status

    def resolved_targets(self) -> list[ResolvedTarget]:
        """Resolve the targets of the experiment into the individual resources.

        Only targets that list their resources by ARN are resolved - moto does
        not look up the resources that a target selects by tag or by filter.
        """
        return [
            ResolvedTarget(
                resource_type=target.get("resourceType", ""),
                target_name=target_name,
                resource_arn=arn,
            )
            for target_name, target in self.targets.items()
            for arn in target.get("resourceArns") or []
        ]

    def to_summary_dict(self, tags: Optional[dict[str, str]] = None) -> dict[str, Any]:
        status = self._sync_state()
        return {
            "id": self.id,
            "arn": self.arn,
            "experimentTemplateId": self.experiment_template_id,
            "state": {
                "status": status,
                "reason": self.STATUS_REASONS.get(status, status),
            },
            "creationTime": self.creation_time,
            "tags": tags or {},
            "experimentOptions": self.experiment_options,
        }

    def to_dict(self, tags: Optional[dict[str, str]] = None) -> dict[str, Any]:
        status = self._sync_state()
        dct: dict[str, Any] = {
            "id": self.id,
            "arn": self.arn,
            "experimentTemplateId": self.experiment_template_id,
            "roleArn": self.role_arn,
            "state": {
                "status": status,
                "reason": self.STATUS_REASONS.get(status, status),
            },
            "targets": self.targets or {},
            "actions": self.actions or {},
            "stopConditions": self.stop_conditions or [],
            "creationTime": self.creation_time,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "tags": tags or {},
            "logConfiguration": self.log_configuration,
            "experimentOptions": self.experiment_options,
            "targetAccountConfigurationsCount": len(self.target_account_configurations),
            "experimentReportConfiguration": self.experiment_report_configuration,
        }
        return {k: v for k, v in dct.items() if v is not None}


class FISBackend(BaseBackend):
    PAGINATION_MODEL = {
        "list_experiment_templates": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "id",
        },
        "list_experiments": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "id",
        },
        "list_experiment_resolved_targets": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": ["target_name", "resource_arn"],
        },
        # This API only takes a nextToken - there is no maxResults parameter.
        "list_experiment_target_account_configurations": {
            "input_token": "next_token",
            "limit_default": 100,
            "unique_attribute": "account_id",
        },
        "list_target_account_configurations": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "account_id",
        },
    }

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.experiment_templates: dict[str, ExperimentTemplate] = {}
        self._client_token_to_template_id: dict[str, str] = {}
        self.experiments: dict[str, Experiment] = {}
        self._client_token_to_experiment_id: dict[str, str] = {}
        self.tagger = TaggingService()

    def create_experiment_template(
        self,
        client_token: Optional[str],
        description: str,
        stop_conditions: list[dict[str, Any]],
        targets: Optional[dict[str, Any]],
        actions: dict[str, Any],
        role_arn: str,
        tags: Optional[dict[str, str]] = None,
        log_configuration: Optional[dict[str, Any]] = None,
        experiment_options: Optional[dict[str, Any]] = None,
        experiment_report_configuration: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        # clientToken is required per the AWS API; auto-populate to match boto3's behaviour.
        token = client_token or str(mock_random.uuid4())
        existing_id = self._client_token_to_template_id.get(token)
        if existing_id and existing_id in self.experiment_templates:
            tmpl = self.experiment_templates[existing_id]
            return tmpl.to_dict(tags=self.tagger.get_tag_dict_for_resource(tmpl.arn))

        template_id = mock_random.uuid4().hex
        now = unix_time()
        template = ExperimentTemplate(
            account_id=self.account_id,
            region_name=self.region_name,
            id=template_id,
            client_token=token,
            description=description,
            stop_conditions=stop_conditions,
            targets=targets or {},
            actions=actions,
            role_arn=role_arn,
            log_configuration=log_configuration,
            experiment_options=experiment_options,
            experiment_report_configuration=experiment_report_configuration,
            creation_time=now,
            last_update_time=now,
        )
        self.experiment_templates[template_id] = template
        self._client_token_to_template_id[token] = template_id
        if tags:
            self.tagger.tag_resource(
                template.arn, TaggingService.convert_dict_to_tags_input(tags)
            )
        return template.to_dict(tags=tags or {})

    def delete_experiment_template(self, id: str) -> dict[str, Any]:
        if id not in self.experiment_templates:
            raise ResourceNotFoundException(f"Experiment template {id} does not exist")
        template = self.experiment_templates.pop(id)
        tags = self.tagger.get_tag_dict_for_resource(template.arn)
        self._client_token_to_template_id.pop(template.client_token, None)
        return template.to_dict(tags=tags)

    def tag_resource(self, resource_arn: str, tags: dict[str, str]) -> None:
        self.tagger.tag_resource(
            resource_arn, TaggingService.convert_dict_to_tags_input(tags or {})
        )
        for tmpl in self.experiment_templates.values():
            if tmpl.arn == resource_arn:
                tmpl.last_update_time = unix_time()
                break

    def untag_resource(self, resource_arn: str, tag_keys: list[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)
        for tmpl in self.experiment_templates.values():
            if tmpl.arn == resource_arn:
                tmpl.last_update_time = unix_time()
                break

    def list_tags_for_resource(self, resource_arn: str) -> dict[str, str]:
        return self.tagger.get_tag_dict_for_resource(resource_arn)

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_experiment_templates(self) -> list[ExperimentTemplate]:
        return list(self.experiment_templates.values())

    def get_experiment_template(self, id: str) -> dict[str, Any]:
        if id not in self.experiment_templates:
            raise ResourceNotFoundException(f"Experiment template {id} does not exist")
        template = self.experiment_templates[id]
        return template.to_dict(
            tags=self.tagger.get_tag_dict_for_resource(template.arn)
        )

    def start_experiment(
        self,
        client_token: Optional[str],
        experiment_template_id: str,
        experiment_options: Optional[dict[str, Any]] = None,
        tags: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        # clientToken is required per the AWS API; auto-populate to match boto3's behaviour.
        token = client_token or str(mock_random.uuid4())
        existing_id = self._client_token_to_experiment_id.get(token)
        if existing_id and existing_id in self.experiments:
            experiment = self.experiments[existing_id]
            return experiment.to_dict(
                tags=self.tagger.get_tag_dict_for_resource(experiment.arn)
            )

        if experiment_template_id not in self.experiment_templates:
            raise ResourceNotFoundException(
                f"Experiment template {experiment_template_id} does not exist"
            )
        template = self.experiment_templates[experiment_template_id]

        # The experiment gets its own copy of the template configuration, so that
        # updating the template afterwards does not change a running experiment.
        actions = deepcopy(template.actions or {})
        for action in actions.values():
            action["state"] = {
                "status": "pending",
                "reason": Experiment.STATUS_REASONS["pending"],
            }

        template_options = template.experiment_options or {}
        now = unix_time()
        experiment = Experiment(
            account_id=self.account_id,
            region_name=self.region_name,
            id=mock_random.uuid4().hex,
            client_token=token,
            experiment_template_id=experiment_template_id,
            role_arn=template.role_arn,
            targets=deepcopy(template.targets or {}),
            actions=actions,
            stop_conditions=deepcopy(template.stop_conditions or []),
            log_configuration=deepcopy(template.log_configuration),
            experiment_options={
                "accountTargeting": template_options.get(
                    "accountTargeting", "single-account"
                ),
                "emptyTargetResolutionMode": template_options.get(
                    "emptyTargetResolutionMode", "fail"
                ),
                "actionsMode": (experiment_options or {}).get("actionsMode", "run-all"),
            },
            experiment_report_configuration=deepcopy(
                template.experiment_report_configuration
            ),
            target_account_configurations=deepcopy(
                template.target_account_configurations
            ),
            creation_time=now,
            start_time=now,
        )
        self.experiments[experiment.id] = experiment
        self._client_token_to_experiment_id[token] = experiment.id
        if tags:
            self.tagger.tag_resource(
                experiment.arn, TaggingService.convert_dict_to_tags_input(tags)
            )
        return experiment.to_dict(tags=tags or {})

    def get_experiment(self, id: str) -> dict[str, Any]:
        if id not in self.experiments:
            raise ResourceNotFoundException(f"Experiment {id} does not exist")
        experiment = self.experiments[id]
        experiment.advance()
        return experiment.to_dict(
            tags=self.tagger.get_tag_dict_for_resource(experiment.arn)
        )

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_experiments(
        self, experiment_template_id: Optional[str] = None
    ) -> list[Experiment]:
        experiments = list(self.experiments.values())
        if experiment_template_id:
            experiments = [
                experiment
                for experiment in experiments
                if experiment.experiment_template_id == experiment_template_id
            ]
        return experiments

    def stop_experiment(self, id: str) -> dict[str, Any]:
        if id not in self.experiments:
            raise ResourceNotFoundException(f"Experiment {id} does not exist")
        experiment = self.experiments[id]
        # Stopping an experiment that already finished leaves it untouched - the
        # AWS API does not expose a ConflictException for StopExperiment.
        if experiment.status not in Experiment.TERMINAL_STATUSES:
            experiment.status = "stopping"
        return experiment.to_dict(
            tags=self.tagger.get_tag_dict_for_resource(experiment.arn)
        )

    def create_target_account_configuration(
        self,
        client_token: Optional[str],
        experiment_template_id: str,
        account_id: str,
        role_arn: str,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        if experiment_template_id not in self.experiment_templates:
            raise ResourceNotFoundException(
                f"Experiment template {experiment_template_id} does not exist"
            )
        template = self.experiment_templates[experiment_template_id]
        config = TargetAccountConfiguration(
            account_id=account_id, role_arn=role_arn, description=description
        )
        template.target_account_configurations[account_id] = config
        return config.to_dict()

    def update_experiment_template(
        self,
        id: str,
        description: Optional[str] = None,
        stop_conditions: Optional[list[dict[str, Any]]] = None,
        targets: Optional[dict[str, Any]] = None,
        actions: Optional[dict[str, Any]] = None,
        role_arn: Optional[str] = None,
        log_configuration: Optional[dict[str, Any]] = None,
        experiment_options: Optional[dict[str, Any]] = None,
        experiment_report_configuration: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if id not in self.experiment_templates:
            raise ResourceNotFoundException(f"Experiment template {id} does not exist")
        template = self.experiment_templates[id]

        # Only the parameters that are supplied are updated - anything omitted
        # keeps its current value.
        if description is not None:
            template.description = description
        if stop_conditions is not None:
            template.stop_conditions = stop_conditions
        if targets is not None:
            template.targets = targets
        if actions is not None:
            template.actions = actions
        if role_arn is not None:
            template.role_arn = role_arn
        if log_configuration is not None:
            template.log_configuration = log_configuration
        if experiment_options is not None:
            # Only emptyTargetResolutionMode can be updated; accountTargeting is
            # fixed when the template is created.
            template.experiment_options = {
                **(template.experiment_options or {}),
                **experiment_options,
            }
        if experiment_report_configuration is not None:
            template.experiment_report_configuration = experiment_report_configuration

        template.last_update_time = unix_time()
        return template.to_dict(
            tags=self.tagger.get_tag_dict_for_resource(template.arn)
        )

    def get_experiment_target_account_configuration(
        self, experiment_id: str, account_id: str
    ) -> dict[str, Any]:
        if experiment_id not in self.experiments:
            raise ResourceNotFoundException(
                f"Experiment {experiment_id} does not exist"
            )
        experiment = self.experiments[experiment_id]
        if account_id not in experiment.target_account_configurations:
            raise ResourceNotFoundException(
                f"Target account configuration for account {account_id} does not exist"
            )
        return experiment.target_account_configurations[account_id].to_dict()

    def _get_target_account_configuration(
        self, experiment_template_id: str, account_id: str
    ) -> TargetAccountConfiguration:
        if experiment_template_id not in self.experiment_templates:
            raise ResourceNotFoundException(
                f"Experiment template {experiment_template_id} does not exist"
            )
        template = self.experiment_templates[experiment_template_id]
        if account_id not in template.target_account_configurations:
            raise ResourceNotFoundException(
                f"Target account configuration for account {account_id} does not exist"
            )
        return template.target_account_configurations[account_id]

    def update_target_account_configuration(
        self,
        experiment_template_id: str,
        account_id: str,
        role_arn: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        config = self._get_target_account_configuration(
            experiment_template_id, account_id
        )

        # Only the parameters that are supplied are updated - anything omitted
        # keeps its current value.
        if role_arn is not None:
            config.role_arn = role_arn
        if description is not None:
            config.description = description
        return config.to_dict()

    def delete_target_account_configuration(
        self, experiment_template_id: str, account_id: str
    ) -> dict[str, Any]:
        config = self._get_target_account_configuration(
            experiment_template_id, account_id
        )
        template = self.experiment_templates[experiment_template_id]
        del template.target_account_configurations[account_id]
        return config.to_dict()

    def get_target_account_configuration(
        self, experiment_template_id: str, account_id: str
    ) -> dict[str, Any]:
        config = self._get_target_account_configuration(
            experiment_template_id, account_id
        )
        return config.to_dict()

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_experiment_resolved_targets(
        self, experiment_id: str, target_name: Optional[str] = None
    ) -> list[ResolvedTarget]:
        if experiment_id not in self.experiments:
            raise ResourceNotFoundException(
                f"Experiment {experiment_id} does not exist"
            )
        resolved_targets = self.experiments[experiment_id].resolved_targets()
        if target_name:
            resolved_targets = [
                target
                for target in resolved_targets
                if target.target_name == target_name
            ]
        return resolved_targets

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_experiment_target_account_configurations(
        self, experiment_id: str
    ) -> list[TargetAccountConfiguration]:
        if experiment_id not in self.experiments:
            raise ResourceNotFoundException(
                f"Experiment {experiment_id} does not exist"
            )
        experiment = self.experiments[experiment_id]
        return list(experiment.target_account_configurations.values())

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_target_account_configurations(
        self, experiment_template_id: str
    ) -> list[TargetAccountConfiguration]:
        if experiment_template_id not in self.experiment_templates:
            raise ResourceNotFoundException(
                f"Experiment template {experiment_template_id} does not exist"
            )
        template = self.experiment_templates[experiment_template_id]
        return list(template.target_account_configurations.values())


fis_backends = BackendDict(
    FISBackend,
    "fis",
    use_boto3_regions=False,
    additional_regions=[
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "af-south-1",
        "ap-east-1",
        "ap-south-1",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-southeast-1",
        "ap-southeast-2",
        "ca-central-1",
        "eu-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-north-1",
        "eu-south-1",
        "me-south-1",
        "sa-east-1",
    ],
)
