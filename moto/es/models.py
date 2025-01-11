from moto.core.base_backend import BackendDict, BaseBackend


class ElasticsearchServiceBackend(BaseBackend):
    def __init__(self, region_name: str, account_id: str):
        # Functionality is part of OpenSearch, as that includes all of ES functionality + more
        super().__init__(region_name, account_id)


es_backends = BackendDict(ElasticsearchServiceBackend, "es")
