"""Handles incoming fis requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import fis_backends


class FISResponse(BaseResponse):
    """Handler for FIS requests and responses."""

    def __init__(self):
        super().__init__(service_name="fis")

    @property
    def fis_backend(self):
        """Return backend instance specific for this region."""
        # TODO
        # fis_backends is not yet typed
        # Please modify moto/backends.py to add the appropriate type annotations for this service
        return fis_backends[self.current_account][self.region]

    # add methods from here

    
    def create_experiment_template(self):
        params = self._get_params()
        client_token = params.get("clientToken")
        description = params.get("description")
        stop_conditions = params.get("stopConditions")
        targets = params.get("targets")
        actions = params.get("actions")
        role_arn = params.get("roleArn")
        tags = params.get("tags")
        log_configuration = params.get("logConfiguration")
        experiment_options = params.get("experimentOptions")
        experiment_report_configuration = params.get("experimentReportConfiguration")
        experiment_template = self.fis_backend.create_experiment_template(
            client_token=client_token,
            description=description,
            stop_conditions=stop_conditions,
            targets=targets,
            actions=actions,
            role_arn=role_arn,
            tags=tags,
            log_configuration=log_configuration,
            experiment_options=experiment_options,
            experiment_report_configuration=experiment_report_configuration,
        )
        # TODO: adjust response
        return json.dumps(dict(experimentTemplate=experiment_template))

    
    def delete_experiment_template(self):
        params = self._get_params()
        id = params.get("id")
        experiment_template = self.fis_backend.delete_experiment_template(
            id=id,
        )
        # TODO: adjust response
        return json.dumps(dict(experimentTemplate=experiment_template))
# add templates from here
    
    def tag_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        tags = params.get("tags")
        self.fis_backend.tag_resource(
            resource_arn=resource_arn,
            tags=tags,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def untag_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        tag_keys = params.get("tagKeys")
        self.fis_backend.untag_resource(
            resource_arn=resource_arn,
            tag_keys=tag_keys,
        )
        # TODO: adjust response
        return json.dumps(dict())
    
    def list_tags_for_resource(self):
        params = self._get_params()
        resource_arn = params.get("resourceArn")
        tags = self.fis_backend.list_tags_for_resource(
            resource_arn=resource_arn,
        )
        # TODO: adjust response
        return json.dumps(dict(tags=tags))
