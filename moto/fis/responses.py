import json
from typing import Any

from moto.core.responses import BaseResponse

from .models import FISBackend, fis_backends


class FISResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="fis")

    @property
    def fis_backend(self) -> FISBackend:
        """Return backend instance specific for this region."""
        return fis_backends[self.current_account][self.region]

    def create_experiment_template(self) -> str:
        experiment_template = self.fis_backend.create_experiment_template(
            client_token=self._get_param("clientToken"),
            description=self._get_param("description"),
            stop_conditions=self._get_param("stopConditions"),
            targets=self._get_param("targets"),
            actions=self._get_param("actions"),
            role_arn=self._get_param("roleArn"),
            tags=self._get_param("tags"),
            log_configuration=self._get_param("logConfiguration"),
            experiment_options=self._get_param("experimentOptions"),
            experiment_report_configuration=self._get_param(
                "experimentReportConfiguration"
            ),
        )
        return json.dumps({"experimentTemplate": experiment_template})

    def delete_experiment_template(self) -> str:
        experiment_template = self.fis_backend.delete_experiment_template(
            id=self._get_param("id")
        )
        return json.dumps({"experimentTemplate": experiment_template})

    def tag_resource(self) -> str:
        self.fis_backend.tag_resource(
            resource_arn=self._get_param("resourceArn"),
            tags=self._get_param("tags"),
        )
        return "{}"

    def untag_resource(self) -> str:
        self.fis_backend.untag_resource(
            resource_arn=self._get_param("resourceArn"),
            tag_keys=self.querystring.get("tagKeys") or [],
        )
        return "{}"

    def list_tags_for_resource(self) -> str:
        tags = self.fis_backend.list_tags_for_resource(
            resource_arn=self._get_param("resourceArn")
        )
        return json.dumps({"tags": tags})

    def list_experiment_templates(self) -> str:
        experiment_templates, next_token = self.fis_backend.list_experiment_templates(
            max_results=self._get_int_param("maxResults"),
            next_token=self._get_param("nextToken"),
        )
        summaries = [
            tmpl.to_summary_dict(tags=self.fis_backend.list_tags_for_resource(tmpl.arn))
            for tmpl in experiment_templates
        ]
        resp: dict[str, Any] = {"experimentTemplates": summaries}
        if next_token:
            resp["nextToken"] = next_token
        return json.dumps(resp)

    def get_experiment_template(self) -> str:
        experiment_template = self.fis_backend.get_experiment_template(
            id=self._get_param("id")
        )
        return json.dumps({"experimentTemplate": experiment_template})

    def start_experiment(self) -> str:
        experiment = self.fis_backend.start_experiment(
            client_token=self._get_param("clientToken"),
            experiment_template_id=self._get_param("experimentTemplateId"),
            experiment_options=self._get_param("experimentOptions"),
            tags=self._get_param("tags"),
        )
        return json.dumps({"experiment": experiment})

    def get_experiment(self) -> str:
        experiment = self.fis_backend.get_experiment(id=self._get_param("id"))
        return json.dumps({"experiment": experiment})

    def list_experiments(self) -> str:
        experiments, next_token = self.fis_backend.list_experiments(
            max_results=self._get_int_param("maxResults"),
            next_token=self._get_param("nextToken"),
            experiment_template_id=self._get_param("experimentTemplateId"),
        )
        summaries = [
            experiment.to_summary_dict(
                tags=self.fis_backend.list_tags_for_resource(experiment.arn)
            )
            for experiment in experiments
        ]
        resp: dict[str, Any] = {"experiments": summaries}
        if next_token:
            resp["nextToken"] = next_token
        return json.dumps(resp)

    def stop_experiment(self) -> str:
        experiment = self.fis_backend.stop_experiment(id=self._get_param("id"))
        return json.dumps({"experiment": experiment})
    
    def create_target_account_configuration(self):
        params = self._get_params()
        client_token = params.get("clientToken")
        experiment_template_id = params.get("experimentTemplateId")
        account_id = params.get("accountId")
        role_arn = params.get("roleArn")
        description = params.get("description")
        target_account_configuration = self.fis_backend.create_target_account_configuration(
            client_token=client_token,
            experiment_template_id=experiment_template_id,
            account_id=account_id,
            role_arn=role_arn,
            description=description,
        )
        # TODO: adjust response
        return json.dumps(dict(targetAccountConfiguration=target_account_configuration))
