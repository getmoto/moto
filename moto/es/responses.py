import json
import re

from functools import wraps
from moto.core.responses import BaseResponse
from .exceptions import ElasticSearchError, InvalidDomainName
from .models import es_backends


def error_handler(f):
    @wraps(f)
    def _wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ElasticSearchError as e:
            return e.code, e.get_headers(), e.get_body()

    return _wrapper


class ElasticsearchServiceResponse(BaseResponse):
    """Handler for ElasticsearchService requests and responses."""

    @property
    def es_backend(self):
        """Return backend instance specific for this region."""
        return es_backends[self.region]

    @classmethod
    @error_handler
    def list_domains(cls, request, full_url, headers):
        response = ElasticsearchServiceResponse()
        response.setup_class(request, full_url, headers)
        if request.method == "GET":
            return response.list_domain_names()

    @classmethod
    @error_handler
    def domains(cls, request, full_url, headers):
        response = ElasticsearchServiceResponse()
        response.setup_class(request, full_url, headers)
        if request.method == "POST":
            return response.create_elasticsearch_domain()

    @classmethod
    @error_handler
    def domain(cls, request, full_url, headers):
        response = ElasticsearchServiceResponse()
        response.setup_class(request, full_url, headers)
        if request.method == "DELETE":
            return response.delete_elasticsearch_domain()
        if request.method == "GET":
            return response.describe_elasticsearch_domain()

    def create_elasticsearch_domain(self):
        params = json.loads(self.body)
        domain_name = params.get("DomainName")
        if not re.match(r"^[a-z][a-z0-9\-]+$", domain_name):
            raise InvalidDomainName(domain_name)
        elasticsearch_version = params.get("ElasticsearchVersion")
        elasticsearch_cluster_config = params.get("ElasticsearchClusterConfig")
        ebs_options = params.get("EBSOptions")
        access_policies = params.get("AccessPolicies")
        snapshot_options = params.get("SnapshotOptions")
        vpc_options = params.get("VPCOptions")
        cognito_options = params.get("CognitoOptions")
        encryption_at_rest_options = params.get("EncryptionAtRestOptions")
        node_to_node_encryption_options = params.get("NodeToNodeEncryptionOptions")
        advanced_options = params.get("AdvancedOptions")
        log_publishing_options = params.get("LogPublishingOptions")
        domain_endpoint_options = params.get("DomainEndpointOptions")
        advanced_security_options = params.get("AdvancedSecurityOptions")
        auto_tune_options = params.get("AutoTuneOptions")
        tag_list = params.get("TagList")
        domain_status = self.es_backend.create_elasticsearch_domain(
            domain_name=domain_name,
            elasticsearch_version=elasticsearch_version,
            elasticsearch_cluster_config=elasticsearch_cluster_config,
            ebs_options=ebs_options,
            access_policies=access_policies,
            snapshot_options=snapshot_options,
            vpc_options=vpc_options,
            cognito_options=cognito_options,
            encryption_at_rest_options=encryption_at_rest_options,
            node_to_node_encryption_options=node_to_node_encryption_options,
            advanced_options=advanced_options,
            log_publishing_options=log_publishing_options,
            domain_endpoint_options=domain_endpoint_options,
            advanced_security_options=advanced_security_options,
            auto_tune_options=auto_tune_options,
            tag_list=tag_list,
        )
        return 200, {}, json.dumps({"DomainStatus": domain_status})

    def delete_elasticsearch_domain(self):
        domain_name = self.path.split("/")[-1]
        self.es_backend.delete_elasticsearch_domain(domain_name=domain_name,)
        return 200, {}, json.dumps(dict())

    def describe_elasticsearch_domain(self):
        domain_name = self.path.split("/")[-1]
        if not re.match(r"^[a-z][a-z0-9\-]+$", domain_name):
            raise InvalidDomainName(domain_name)
        domain_status = self.es_backend.describe_elasticsearch_domain(
            domain_name=domain_name,
        )
        return 200, {}, json.dumps({"DomainStatus": domain_status})

    def list_domain_names(self):
        params = self._get_params()
        engine_type = params.get("EngineType")
        domain_names = self.es_backend.list_domain_names(engine_type=engine_type,)
        return 200, {}, json.dumps({"DomainNames": domain_names})
