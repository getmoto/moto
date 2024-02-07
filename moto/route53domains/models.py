from datetime import datetime, timezone
from typing import Dict, List

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel


class Route53Domain(BaseModel):
    def __init__(self,
                 account_id: str,
                 region: str,
                 domain_name: str,
                 idn_lang_code: str,
                 duration_in_years: int,
                 auto_renew: bool,
                 admin_contact: Dict[str, str | List[Dict[str, str]]],
                 registrant_contact: Dict[str, str | List[Dict[str, str]]],
                 tech_contact: Dict[str, str | List[Dict[str, str]]],
                 admin_privacy: bool,
                 registrant_privacy: bool,
                 tech_privacy: bool,
                 ):
        self.account_id = account_id,
        self.region = region,
        self.domain_name = domain_name,
        self.idn_lang_code = idn_lang_code,
        self.duration_in_years = duration_in_years,
        self.auto_renew = auto_renew,
        self.admin_contact = admin_contact
        self.registrant_contact = registrant_contact
        self.tech_contact = tech_contact
        self.admin_privacy = admin_privacy
        self.registrant_privacy = registrant_privacy
        self.tech_privacy = tech_privacy
        self.registrar_name = 'AWS'
        self.who_is_server = 'AWS-WHOIS-SERVER'
        self.registrar_url = 'registrar.aws.amazon.com'
        self.abuse_contact_email = 'abuse@aws.com'
        self.abuse_contact_phone = '+1111111111'
        self.registry_domain_id = ''
        self.creation_date = datetime.now(timezone.utc).isoformat()
        self.updated_date = datetime.now(timezone.utc).isoformat()
        self.expiration_date = datetime.now(timezone.utc).isoformat()
        self.reseller = 'Amazon'
        self.dns_sec = 'Deprecated'
        self.status_list = ['ok']
        self.dns_sec_keys = [{
            'Algorithm': 13,  # Always 13 for Route53 domains
            'Flags': 257,  # Code for KSK - Key Singing Key
            'PublicKey': 'some-public-key-in-base-64',
            'DigestType': 1,  # SHA1
            'Digest': 'some-digest',
            'KeyTag': 123,
            'Id': 'some-id'
        }]


class Route53DomainsBackend(BaseBackend):
    """Implementation of Route53Domains APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.domains: Dict[str, Route53Domain] = {}

    def register_domain(self,
                        domain_name: str,
                        idn_lang_code: str,
                        duration_in_years: int,
                        auto_renew: bool,
                        admin_contact: Dict[str, str | List[Dict[str, str]]],
                        registrant_contact: Dict[str, str | List[Dict[str, str]]],
                        tech_contact: Dict[str, str | List[Dict[str, str]]],
                        private_protect_admin_contact: bool,
                        private_protect_registrant_contact: bool,
                        private_protect_tech_contact: bool,
                        ):
        route53_domain = Route53Domain(
            account_id=self.account_id,
            region=self.region_name,
            domain_name=domain_name,
            idn_lang_code=idn_lang_code,
            duration_in_years=duration_in_years,
            auto_renew=auto_renew,
            admin_contact=admin_contact,
            registrant_contact=registrant_contact,
            tech_contact=tech_contact,
            admin_privacy=private_protect_admin_contact,
            registrant_privacy=private_protect_registrant_contact,
            tech_privacy=private_protect_tech_contact
        )

        self.domains[domain_name] = route53_domain
        return route53_domain


route53domains_backends = BackendDict(Route53DomainsBackend, "route53domains")
