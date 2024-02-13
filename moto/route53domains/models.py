from datetime import datetime, timezone, timedelta
from typing import Dict, List

from moto.core.base_backend import BaseBackend, BackendDict
from moto.route53 import route53_backends
from moto.route53.models import Route53Backend
from .validators import Route53Domain, Route53DomainsOperation


class Route53DomainsBackend(BaseBackend):
    """Implementation of Route53Domains APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.__route53_backend: Route53Backend = route53_backends[account_id]['global']
        self.__domains: Dict[str, Route53Domain] = {}
        self.__operations: Dict[str, Route53DomainsOperation] = {}

    def register_domain(self,
                        domain_name: str,
                        duration_in_years: int,
                        auto_renew: bool,
                        admin_contact: Dict,
                        registrant_contact: Dict,
                        tech_contact: Dict,
                        private_protect_admin_contact: bool,
                        private_protect_registrant_contact: bool,
                        private_protect_tech_contact: bool,
                        extra_params: List[Dict]
                        ) -> Route53DomainsOperation:

        expiration_date = datetime.now(timezone.utc) + timedelta(days=365*duration_in_years)

        domain = Route53Domain.model_validate({
            'DomainName': domain_name,
            'AutoRenew': auto_renew,
            'AdminContact': admin_contact,
            'RegistrantContact': registrant_contact,
            'TechContact': tech_contact,
            'AdminPrivacy': private_protect_admin_contact,
            'RegistrantPrivacy': private_protect_registrant_contact,
            'TechPrivacy': private_protect_tech_contact,
            'ExpirationDate': expiration_date.isoformat(),
            'StatusList': ['OK'],
            'ExtraParams': extra_params
        })

        operation = Route53DomainsOperation.model_validate({
            'DomainName': domain_name,
            'Status': 'SUCCESSFUL',
            'Type': 'REGISTER_DOMAIN',
            'StatusFlag': 'PENDING_ACCEPTANCE'
        })

        self.__operations[operation.id_] = operation

        self.__route53_backend.create_hosted_zone(
            name=domain.domain_name,
            private_zone=False
        )

        self.__domains[domain_name] = domain
        return operation

    # TODO: Add and handle parameters
    def list_operations(self) -> List[Route53DomainsOperation]:
        return list(self.__operations.values())


route53domains_backends = BackendDict(
    Route53DomainsBackend, "route53domains", use_boto3_regions=False, additional_regions=['global'])
