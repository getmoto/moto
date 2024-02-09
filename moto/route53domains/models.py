from datetime import datetime, timezone
from typing import Dict, List, Literal

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.moto_api._internal import MotoRandom
from moto.route53 import route53_backends
from moto.route53.models import Route53Backend


class Route53DomainsOperation(BaseModel):
    def __init__(self,
                 operation_id: str,
                 status: Literal['SUBMITTED', 'IN_PROGRESS', 'ERROR', 'SUCCESSFUL', 'FAILED'],
                 operation_type: Literal[
                     'REGISTER_DOMAIN', 'DELETE_DOMAIN', 'TRANSFER_IN_DOMAIN', 'UPDATE_DOMAIN_CONTACT', 'UPDATE_NAMESERVER', 'CHANGE_PRIVACY_PROTECTION', 'DOMAIN_LOCK', 'ENABLE_AUTORENEW', 'DISABLE_AUTORENEW', 'ADD_DNSSEC', 'REMOVE_DNSSEC', 'EXPIRE_DOMAIN', 'TRANSFER_OUT_DOMAIN', 'CHANGE_DOMAIN_OWNER', 'RENEW_DOMAIN', 'PUSH_DOMAIN', 'INTERNAL_TRANSFER_OUT_DOMAIN', 'INTERNAL_TRANSFER_IN_DOMAIN'],
                 submitted_date: datetime,
                 domain_name: str,
                 message: str,
                 status_flag: Literal[
                     'PENDING_ACCEPTANCE', 'PENDING_CUSTOMER_ACTION', 'PENDING_AUTHORIZATION', 'PENDING_PAYMENT_VERIFICATION', 'PENDING_SUPPORT_CASE'],
                 last_updated_date: datetime
                 ):
        self.operation_id = operation_id
        self.status = status
        self.operation_type = operation_type
        self.submitted_date = submitted_date
        self.domain_name = domain_name
        self.message = message
        self.status_flag = status_flag
        self.last_updated_date = last_updated_date

    def to_json(self) -> Dict:
        return {
            'OperationId': self.operation_id,
            'Status': self.status,
            'Type': self.operation_type,
            'SubmittedDate': self.submitted_date.isoformat(),
            'DomainName': self.domain_name,
            'Message': self.message,
            'StatusFlag': self.status_flag,
            'LastUpdatedDate': self.last_updated_date.isoformat()
        }


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
        self.domain_name = domain_name
        self.idn_lang_code = idn_lang_code
        self.duration_in_years = duration_in_years
        self.auto_renew = auto_renew
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
        self.__route53_backend: Route53Backend = route53_backends[account_id]['global']
        self.domains: Dict[str, Route53Domain] = {}
        self.operations: Dict[str, Route53DomainsOperation] = {}

    # TODO: Validate parameters
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
                        ) -> Route53DomainsOperation:

        operation = Route53DomainsOperation(
            operation_id=str(MotoRandom().uuid4()),
            status='SUBMITTED',
            operation_type='REGISTER_DOMAIN',
            submitted_date=datetime.now(timezone.utc),
            domain_name=domain_name,
            message='',
            status_flag='PENDING_ACCEPTANCE',
            last_updated_date=datetime.now(timezone.utc)
        )

        self.operations[operation.operation_id] = operation

        domain = Route53Domain(
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

        self.__route53_backend.create_hosted_zone(
            name=domain.domain_name,
            private_zone=False
        )

        self.domains[domain_name] = domain
        return operation

    # TODO: Add and handle parameters
    def list_operations(self) -> List[Route53DomainsOperation]:
        return list(self.operations.values())


route53domains_backends = BackendDict(
    Route53DomainsBackend, "route53domains", use_boto3_regions=False, additional_regions=['global'])
