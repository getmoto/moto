from typing import Any, Dict, List, Optional

from moto.core.base_backend import BackendDict, BaseBackend
from moto.core.common_models import BaseModel
from moto.moto_api._internal import mock_random
from moto.utilities.utils import get_partition

from .exceptions import DomainNotFound, EngineTypeNotFoundException


class Domain(BaseModel):
    def __init__(
        self,
        region_name: str,
        domain_name: str,
        es_version: str,
        elasticsearch_cluster_config: Dict[str, Any],
        ebs_options: Dict[str, Any],
        access_policies: Dict[str, Any],
        snapshot_options: Dict[str, Any],
        vpc_options: Dict[str, Any],
        cognito_options: Dict[str, Any],
        encryption_at_rest_options: Dict[str, Any],
        node_to_node_encryption_options: Dict[str, Any],
        advanced_options: Dict[str, Any],
        log_publishing_options: Dict[str, Any],
        domain_endpoint_options: Dict[str, Any],
        advanced_security_options: Dict[str, Any],
        auto_tune_options: Dict[str, Any],
    ):
        self.domain_id = mock_random.get_random_hex(8)
        self.region_name = region_name
        self.domain_name = domain_name
        self.es_version = es_version
        self.elasticsearch_cluster_config = elasticsearch_cluster_config
        self.ebs_options = ebs_options
        self.access_policies = access_policies
        self.snapshot_options = snapshot_options
        self.vpc_options = vpc_options
        self.cognito_options = cognito_options
        self.encryption_at_rest_options = encryption_at_rest_options
        self.node_to_node_encryption_options = node_to_node_encryption_options
        self.advanced_options = advanced_options
        self.log_publishing_options = log_publishing_options
        self.domain_endpoint_options = domain_endpoint_options
        self.advanced_security_options = advanced_security_options
        self.auto_tune_options = auto_tune_options
        if self.auto_tune_options:
            self.auto_tune_options["State"] = "ENABLED"

    @property
    def arn(self) -> str:
        return f"arn:{get_partition(self.region_name)}:es:{self.region_name}:domain/{self.domain_id}"

    def to_json(self) -> Dict[str, Any]:
        return {
            "DomainId": self.domain_id,
            "DomainName": self.domain_name,
            "ARN": self.arn,
            "Created": True,
            "Deleted": False,
            "Processing": False,
            "UpgradeProcessing": False,
            "ElasticsearchVersion": self.es_version,
            "ElasticsearchClusterConfig": self.elasticsearch_cluster_config,
            "EBSOptions": self.ebs_options,
            "AccessPolicies": self.access_policies,
            "SnapshotOptions": self.snapshot_options,
            "VPCOptions": self.vpc_options,
            "CognitoOptions": self.cognito_options,
            "EncryptionAtRestOptions": self.encryption_at_rest_options,
            "NodeToNodeEncryptionOptions": self.node_to_node_encryption_options,
            "AdvancedOptions": self.advanced_options,
            "LogPublishingOptions": self.log_publishing_options,
            "DomainEndpointOptions": self.domain_endpoint_options,
            "AdvancedSecurityOptions": self.advanced_security_options,
            "AutoTuneOptions": self.auto_tune_options,
        }


class DomainManagerBackend(BaseBackend):
    domains: Dict[str, Dict[str, Domain]] = dict(
        Elasticsearch=dict(), OpenSearch=dict()
    )

    def __init__(self, region_name: str, account_id: str, engine_type: str):
        super().__init__(region_name, account_id)

        if not self._is_valid_engine_type(engine_type):
            raise ValueError(f"Unsupported engine type: {engine_type}")

        self.engine_type = engine_type

    @classmethod
    def reset(cls):
        """Reset shared class-level state."""
        cls.domains = dict(Elasticsearch=dict(), OpenSearch=dict())
        print("Resetting DomainManagerBackend state")
        print(cls.domains)

    def _is_valid_engine_type(self, engine_type) -> bool:
        return engine_type in ["Elasticsearch", "OpenSearch"]

    def add_domain(self, domain_name: str, domain: Domain) -> None:
        print(self.engine_type)
        DomainManagerBackend.domains[self.engine_type][domain_name] = domain

    def delete_domain(self, domain_name: str) -> None:
        if domain_name not in DomainManagerBackend.domains[self.engine_type]:
            raise DomainNotFound(domain_name)
        del DomainManagerBackend.domains[self.engine_type][domain_name]

    def get_domain(self, domain_name: str) -> Domain:
        if domain_name in DomainManagerBackend.domains[self.engine_type]:
            return DomainManagerBackend.domains[self.engine_type][domain_name]
        return None

    def list_domain_names(
        self, engine_type: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Pagination is not yet implemented.
        """
        domain_list = []

        print(DomainManagerBackend.domains)
        if engine_type:
            if not self._is_valid_engine_type(engine_type):
                raise EngineTypeNotFoundException(engine_type)

            domains = DomainManagerBackend.domains[engine_type]
            for name in domains:
                domain_list.append({"DomainName": name, "EngineType": engine_type})

        else:
            for domain_engine_type, domains in DomainManagerBackend.domains.items():
                for name in domains:
                    domain_list.append(
                        {"DomainName": name, "EngineType": domain_engine_type}
                    )

        return domain_list


class ElasticsearchServiceBackend(DomainManagerBackend):
    """Implementation of ElasticsearchService APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id, "Elasticsearch")

    def create_elasticsearch_domain(
        self,
        domain_name: str,
        elasticsearch_version: str,
        elasticsearch_cluster_config: Dict[str, Any],
        ebs_options: Dict[str, Any],
        access_policies: Dict[str, Any],
        snapshot_options: Dict[str, Any],
        vpc_options: Dict[str, Any],
        cognito_options: Dict[str, Any],
        encryption_at_rest_options: Dict[str, Any],
        node_to_node_encryption_options: Dict[str, Any],
        advanced_options: Dict[str, Any],
        log_publishing_options: Dict[str, Any],
        domain_endpoint_options: Dict[str, Any],
        advanced_security_options: Dict[str, Any],
        auto_tune_options: Dict[str, Any],
    ) -> Dict[str, Any]:
        # TODO: Persist/Return other attributes
        new_domain = Domain(
            region_name=self.region_name,
            domain_name=domain_name,
            es_version=elasticsearch_version,
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
        )
        self.add_domain(domain_name, new_domain)
        return new_domain.to_json()

    def delete_elasticsearch_domain(self, domain_name: str) -> None:
        self.delete_domain(domain_name)

    def describe_elasticsearch_domain(self, domain_name: str) -> Dict[str, Any]:
        domain = self.get_domain(domain_name)
        if domain:
            return domain.to_json()
        else:
            raise DomainNotFound(domain_name)

    def describe_elasticsearch_domains(
        self, domain_names: List[str]
    ) -> List[Dict[str, Any]]:
        queried_domains = []
        for domain_name in domain_names:
            domain = self.get_domain(domain_name)
            if domain:
                queried_domains.append(domain.to_json())
        return queried_domains


es_backends = BackendDict(ElasticsearchServiceBackend, "es")
