"""FISBackend class with methods for supported APIs."""

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class FISBackend(BaseBackend):
    """Implementation of FIS APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def create_experiment_template(self, client_token, description, stop_conditions, targets, actions, role_arn, tags, log_configuration, experiment_options, experiment_report_configuration):
        # implement here
        return experiment_template
    
    def delete_experiment_template(self, id):
        # implement here
        return experiment_template
    
    def tag_resource(self, resource_arn, tags):
        # implement here
        return 
    
    def untag_resource(self, resource_arn, tag_keys):
        # implement here
        return 
    
    def list_tags_for_resource(self, resource_arn):
        # implement here
        return tags
    

fis_backends = BackendDict(FISBackend, "fis", additional_regions=["us-east-1"])
