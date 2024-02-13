import json
from typing import Dict, List

from moto.core.responses import BaseResponse
from moto.route53domains.models import Route53DomainsBackend, route53domains_backends


class Route53DomainsResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="route53-domains")

    @property
    def route53domains_backend(self) -> Route53DomainsBackend:
        """Return backend instance specific for this region."""
        return route53domains_backends[self.current_account]['global']

    # TODO: Validate parameters
    def register_domain(self) -> str:
        domain_name: str = self._get_param('DomainName')
        duration_in_years: int = self._get_int_param('DurationInYears')
        auto_renew: bool = self._get_bool_param('AutoRenew', if_none=True)
        admin_contact: Dict = self._get_param('AdminContact')
        registrant_contact: Dict = self._get_param('RegistrantContact')
        tech_contact: Dict = self._get_param('TechContact')
        privacy_protection_admin_contact: bool = self._get_bool_param('PrivacyProtectAdminContact', if_none=True)
        privacy_protection_registrant_contact: bool = self._get_bool_param('PrivacyProtectRegistrantContact', if_none=True)
        privacy_protection_tech_contact: bool = self._get_bool_param('PrivacyProtectTechContact', if_none=True)
        extra_params: List[Dict] = self._get_param('ExtraParams', if_none=[])

        operation = self.route53domains_backend.register_domain(
            domain_name=domain_name,
            duration_in_years=duration_in_years,
            auto_renew=auto_renew,
            admin_contact=admin_contact,
            registrant_contact=registrant_contact,
            tech_contact=tech_contact,
            private_protect_admin_contact=privacy_protection_admin_contact,
            private_protect_registrant_contact=privacy_protection_registrant_contact,
            private_protect_tech_contact=privacy_protection_tech_contact,
            extra_params=extra_params
        )

        return json.dumps({'OperationId': operation.id_})

    # TODO: Add and handle parameters
    def list_operations(self):
        return json.dumps({'Operations': [operation.model_dump(by_alias=True) for operation in self.route53domains_backend.list_operations()]})
