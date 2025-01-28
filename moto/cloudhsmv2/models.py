"""CloudHSMV2Backend class with methods for supported APIs."""

from moto.core.base_backend import BackendDict, BaseBackend


class CloudHSMV2Backend(BaseBackend):
    """Implementation of CloudHSMV2 APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)

    # add methods from here

    def list_tags(self, resource_id, next_token, max_results):
        # implement here
        return tag_list, next_token


cloudhsmv2_backends = BackendDict(CloudHSMV2Backend, "cloudhsmv2")
