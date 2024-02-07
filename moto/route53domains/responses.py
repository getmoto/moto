import json

from moto.core.responses import BaseResponse
from moto.route53domains.models import Route53DomainsBackend, route53domains_backends


class Route53DomainsResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="route53-domains")

    @property
    def route53domains_backend(self) -> Route53DomainsBackend:
        """Return backend instance specific for this region."""
        return route53domains_backends[self.current_account][self.region]

    def register_domain(self) -> str:
        domain_name = self._get_param('DomainName')
        idn_lang_code = self._get_param('IdnLangCode')
        duration_in_years = self._get_param('DurationInYears')
        auto_renew = self._get_param('AutoRenew')
        admin_contact = self._get_param('AdminContact')
        registrant_contact = self._get_param('RegistrantContact')
        tech_contact = self._get_param('TechContact')
        privacy_protection_admin_contact = self._get_param('PrivacyProtectAdminContact')
        privacy_protection_registrant_contact = self._get_param('PrivacyProtectRegistrantContact')
        privacy_protection_tech_contact = self._get_param('PrivacyProtectTechContact')

        domain = self.route53domains_backend.register_domain(
            domain_name=domain_name,
            idn_lang_code=idn_lang_code,
            duration_in_years=duration_in_years,
            auto_renew=auto_renew,
            admin_contact=admin_contact,
            registrant_contact=registrant_contact,
            tech_contact=tech_contact,
            private_protect_admin_contact=privacy_protection_admin_contact,
            private_protect_registrant_contact=privacy_protection_registrant_contact,
            private_protect_tech_contact=privacy_protection_tech_contact,
        )

        return json.dumps({'OperationId': '123'})
