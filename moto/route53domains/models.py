from datetime import datetime, timezone, timedelta
from ipaddress import IPv4Address
from typing import Dict, List, Literal

from pydantic import BaseModel as PydanticBaseModel, Field, model_validator, field_serializer

from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
from moto.moto_api._internal import MotoRandom
from moto.route53 import route53_backends
from moto.route53.models import Route53Backend

DomainOperationStatus = Literal['SUBMITTED', 'IN_PROGRESS', 'ERROR', 'SUCCESSFUL', 'FAILED']

DomainOperationType = Literal['REGISTER_DOMAIN', 'DELETE_DOMAIN', 'TRANSFER_IN_DOMAIN', 'UPDATE_DOMAIN_CONTACT',
                              'UPDATE_NAMESERVER', 'CHANGE_PRIVACY_PROTECTION', 'DOMAIN_LOCK', 'ENABLE_AUTORENEW',
                              'DISABLE_AUTORENEW', 'ADD_DNSSEC', 'REMOVE_DNSSEC', 'EXPIRE_DOMAIN',
                              'TRANSFER_OUT_DOMAIN', 'CHANGE_DOMAIN_OWNER', 'RENEW_DOMAIN', 'PUSH_DOMAIN',
                              'INTERNAL_TRANSFER_OUT_DOMAIN', 'INTERNAL_TRANSFER_IN_DOMAIN']

DomainOperationStatusFlag = Literal['PENDING_ACCEPTANCE', 'PENDING_CUSTOMER_ACTION', 'PENDING_AUTHORIZATION',
                                    'PENDING_PAYMENT_VERIFICATION', 'PENDING_SUPPORT_CASE']

DomainContactDetailContactType = Literal['PERSON', 'COMPANY', 'ASSOCIATION', 'PUBLIC_BODY', 'RESELLER']

DomainContactDetailCountryCode = Literal['AC', 'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AN', 'AO', 'AQ', 'AR', 'AS',
                                         'AT', 'AU', 'AW', 'AX', 'AZ', 'BA', 'BB', 'BD', 'BE', 'BF', 'BG', 'BH', 'BI',
                                         'BJ', 'BL', 'BM', 'BN', 'BO', 'BQ', 'BR', 'BS', 'BT', 'BV', 'BW', 'BY', 'BZ',
                                         'CA', 'CC', 'CD', 'CF', 'CG', 'CH', 'CI', 'CK', 'CL', 'CM', 'CN', 'CO', 'CR',
                                         'CU', 'CV', 'CW', 'CX', 'CY', 'CZ', 'DE', 'DJ', 'DK', 'DM', 'DO', 'DZ', 'EC',
                                         'EE', 'EG', 'EH', 'ER', 'ES', 'ET', 'FI', 'FJ', 'FK', 'FM', 'FO', 'FR', 'GA',
                                         'GB', 'GD', 'GE', 'GF', 'GG', 'GH', 'GI', 'GL', 'GM', 'GN', 'GP', 'GQ', 'GR',
                                         'GS', 'GT', 'GU', 'GW', 'GY', 'HK', 'HM', 'HN', 'HR', 'HT', 'HU', 'ID', 'IE',
                                         'IL', 'IM', 'IN', 'IO', 'IQ', 'IR', 'IS', 'IT', 'JE', 'JM', 'JO', 'JP', 'KE',
                                         'KG', 'KH', 'KI', 'KM', 'KN', 'KP', 'KR', 'KW', 'KY', 'KZ', 'LA', 'LB', 'LC',
                                         'LI', 'LK', 'LR', 'LS', 'LT', 'LU', 'LV', 'LY', 'MA', 'MC', 'MD', 'ME', 'MF',
                                         'MG', 'MH', 'MK', 'ML', 'MM', 'MN', 'MO', 'MP', 'MQ', 'MR', 'MS', 'MT', 'MU',
                                         'MV', 'MW', 'MX', 'MY', 'MZ', 'NA', 'NC', 'NE', 'NF', 'NG', 'NI', 'NL', 'NO',
                                         'NP', 'NR', 'NU', 'NZ', 'OM', 'PA', 'PE', 'PF', 'PG', 'PH', 'PK', 'PL', 'PM',
                                         'PN', 'PR', 'PS', 'PT', 'PW', 'PY', 'QA', 'RE', 'RO', 'RS', 'RU', 'RW', 'SA',
                                         'SB', 'SC', 'SD', 'SE', 'SG', 'SH', 'SI', 'SJ', 'SK', 'SL', 'SM', 'SN', 'SO',
                                         'SR', 'SS', 'ST', 'SV', 'SX', 'SY', 'SZ', 'TC', 'TD', 'TF', 'TG', 'TH', 'TJ',
                                         'TK', 'TL', 'TM', 'TN', 'TO', 'TP', 'TR', 'TT', 'TV', 'TW', 'TZ', 'UA', 'UG',
                                         'US', 'UY', 'UZ', 'VA', 'VC', 'VE', 'VG', 'VI', 'VN', 'VU', 'WF', 'WS', 'YE',
                                         'YT', 'ZA', 'ZM', 'ZW']

# List of supported top-level domains that you can register with Amazon Route53
AWS_SUPPORTED_TLDS = ['.ac', '.academy', '.accountants', '.actor', '.adult', '.agency', '.airforce', '.apartments',
                      '.associates', '.auction', '.audio', '.band', '.bargains', '.bet', '.bike', '.bingo', '.biz',
                      '.black', '.blue', '.boutique', '.builders', '.business', '.buzz', '.cab', '.cafe', '.camera',
                      '.camp', '.capital', '.cards', '.care', '.careers', '.cash', '.casino', '.catering', '.cc',
                      '.center', '.ceo', '.chat', '.cheap', '.church', '.city', '.claims', '.cleaning', '.click',
                      '.clinic', '.clothing', '.cloud', '.club', '.coach', '.codes', '.coffee', '.college', '.com',
                      '.community', '.company', '.computer', '.condos', '.construction', '.consulting', '.contractors',
                      '.cool', '.coupons', '.credit', '.creditcard', '.cruises', '.dance', '.dating', '.deals',
                      '.degree', '.delivery', '.democrat', '.dental', '.diamonds', '.diet', '.digital', '.direct',
                      '.directory', '.discount', '.dog', '.domains', '.education', '.email', '.energy', '.engineering',
                      '.enterprises', '.equipment', '.estate', '.events', '.exchange', '.expert', '.exposed',
                      '.express', '.fail', '.farm', '.finance', '.financial', '.fish', '.fitness', '.flights',
                      '.florist', '.flowers', '.fm', '.football', '.forsale', '.foundation', '.fund', '.furniture',
                      '.futbol', '.fyi', '.gallery', '.games', '.gift', '.gifts', '.gives', '.glass', '.global',
                      '.gmbh', '.gold', '.golf', '.graphics', '.gratis', '.green', '.gripe', '.group', '.guide',
                      '.guitars', '.guru', '.haus', '.healthcare', '.help', '.hiv', '.hockey', '.holdings', '.holiday',
                      '.host', '.hosting', '.house', '.im', '.immo', '.immobilien', '.industries', '.info', '.ink',
                      '.institute', '.insure', '.international', '.investments', '.io', '.irish', '.jewelry', '.juegos',
                      '.kaufen', '.kim', '.kitchen', '.kiwi', '.land', '.lease', '.legal', '.lgbt', '.life',
                      '.lighting', '.limited', '.limo', '.link', '.live', '.loan', '.loans', '.lol', '.maison',
                      '.management', '.marketing', '.mba', '.media', '.memorial', '.mobi', '.moda', '.money',
                      '.mortgage', '.movie', '.name', '.net', '.network', '.news', '.ninja', '.onl', '.online', '.org',
                      '.partners', '.parts', '.photo', '.photography', '.photos', '.pics', '.pictures', '.pink',
                      '.pizza', '.place', '.plumbing', '.plus', '.poker', '.porn', '.press', '.pro', '.productions',
                      '.properties', '.property', '.pub', '.qpon', '.recipes', '.red', '.reise', '.reisen', '.rentals',
                      '.repair', '.report', '.republican', '.restaurant', '.reviews', '.rip', '.rocks', '.run', '.sale',
                      '.sarl', '.school', '.schule', '.services', '.sex', '.sexy', '.shiksha', '.shoes', '.show',
                      '.singles', '.site', '.soccer', '.social', '.solar', '.solutions', '.space', '.store', '.studio',
                      '.style', '.sucks', '.supplies', '.supply', '.support', '.surgery', '.systems', '.tattoo', '.tax',
                      '.taxi', '.team', '.tech', '.technology', '.tennis', '.theater', '.tienda', '.tips', '.tires',
                      '.today', '.tools', '.tours', '.town', '.toys', '.trade', '.training', '.tv', '.university',
                      '.uno', '.vacations', '.vegas', '.ventures', '.vg', '.viajes', '.video', '.villas', '.vision',
                      '.voyage', '.watch', '.website', '.wedding', '.wiki', '.wine', '.works', '.world', '.wtf', '.xyz',
                      '.zone']

AWS_TLDS_REGEX_CAPTURE_GROUP = f'({'|'.join(AWS_SUPPORTED_TLDS)})'
AWS_ROUTE53_DOMAIN_REGEX = rf'^([a-z0-9\.-])+\.{AWS_TLDS_REGEX_CAPTURE_GROUP}$'


class BaseModelMeta(type(PydanticBaseModel), type(BaseModel)):
    pass


class Route53DomainsOperation(PydanticBaseModel, BaseModel, metaclass=BaseModelMeta):
    id_: str = Field(serialization_alias='OperationId', default_factory=lambda: str(MotoRandom().uuid4()))
    status: DomainOperationStatus = Field(serialization_alias='Status')
    type_: DomainOperationType = Field(serialization_alias='Type')
    submitted_date: datetime = Field(serialization_alias='SubmittedDate', default_factory=lambda: datetime.now(timezone.utc))
    domain_name: str = Field(serialization_alias='DomainName')
    message: str = Field(serialization_alias='Message')
    status_flag: DomainOperationStatusFlag = Field(serialization_alias='StatusFlag')
    last_updated_date: datetime = Field(serialization_alias='LastUpdatedDate', default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer('submitted_date', 'last_updated_date')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class Route53DomainsContactDetail(PydanticBaseModel):
    address_line_1: str | None = Field(serialization_alias='AddressLine1', max_length=255),
    address_line_2: str | None = Field(serialization_alias='AddressLine2', max_length=255),
    city: str | None = Field(serialization_alias='City', max_length=255),
    contact_type: DomainContactDetailContactType | None = Field(serialization_alias='ContactType'),
    country_code: DomainContactDetailCountryCode | None = Field(serialization_alias='CountryCode'),
    email: str | None = Field(serialization_alias='Email', max_length=254),
    extra_params: List[Dict] | None = Field(serialization_alias='ExtraParams'),
    fax: str | None = Field(serialization_alias='Fax', pattern=r'\+[0-9]+\.[0-9]+', max_length=30),
    first_name: str | None = Field(serialization_alias='FirstName', max_length=255),
    last_name: str | None = Field(serialization_alias='LastName', max_length=255),
    organization_name: str | None = Field(serialization_alias='OrganizationName', max_length=255),
    phone_number: str | None = Field(serialization_alias='PhoneNumber', pattern=r'\+[0-9]+\.[0-9]+'),
    state: str | None = Field(serialization_alias='State', max_length=255),
    zip_code: str | None = Field(serialization_alias='ZipCode', max_length=255, default='1')

    @model_validator(mode='after')
    def validate_contact_type(self):
        if self.contact_type != 'PERSON' and not self.organization_name:
            raise ValueError('Must specify OrganizationName when ContactType is not PERSON')
        return self


class NameServer(PydanticBaseModel):
    name: str = Field(serialization_alias='Name')
    glue_ips: List[str] = Field(serialization_alias='GlueIps')


class Route53Domain(PydanticBaseModel, BaseModel, metaclass=BaseModelMeta):
    domain_name: str = Field(serialization_alias='DomainName')
    name_servers: List[NameServer] = Field(validate_alias='Nameservers', default=[NameServer(name='dns1.aws.amazon.com', glue_ips=['1.1.1.1'])])
    auto_renew: bool = Field(serialization_alias='AutoRenew', default=True)
    admin_contact: Route53DomainsContactDetail | None = Field(serialization_alias='AdminContact')
    registrant_contact: Route53DomainsContactDetail | None = Field(serialization_alias='RegistrantContact')
    tech_contact: Route53DomainsContactDetail | None = Field(serialization_alias='TechContact')
    admin_privacy: bool = Field(serialization_alias='AdminPrivacy', default=True)
    registrant_privacy: bool = Field(serialization_alias='RegistrantPrivacy', default=True)
    tech_privacy: bool = Field(serialization_alias='TechPrivacy', default=True)
    registrar_name: str = Field(serialization_alias='RegistrarName', default='AMAZON')
    whois_server: str = Field(serialization_alias='WhoIsServer', default='whois.aws.com')  # TODO: Fix default value
    registrar_url: str = Field(serialization_alias='RegistrarUrl', default='https://aws.amazon.com')  # TODO: Fix default value
    abuse_contact_email: str = Field(serialization_alias='AbuseContactEmail', default='abuse@aws.com')
    abuse_contact_phone: str = Field(serialization_alias='AbuseContactPhone', default='+11234567890')
    registry_domain_id: str = Field(serialization_alias='RegistryDomainId', default='')  # Reserved for future use
    creation_date: datetime = Field(serialization_alias='CreationDate', default_factory=lambda: datetime.now(timezone.utc))
    updated_date: datetime = Field(serialization_alias='CreationDate', default_factory=lambda: datetime.now(timezone.utc))
    expiration_date: datetime = Field(serialization_alias='CreationDate', default_factory=lambda: datetime.now(timezone.utc))
    reseller: str = Field(serialization_alias='Reseller', default='Amazon')
    status_list: List[DomainOperationStatus] = Field(serialization_alias='StatusList')
    dns_sec_keys: List[Dict] = Field(serialization_alias='DnssecKeys', default=[{
        'Algorithm': 13,  # Always 13 for Route53 domains
        'Flags': 257,  # Code for KSK - Key Singing Key
        'PublicKey': 'some-public-key-in-base-64',
        'DigestType': 1,  # SHA1
        'Digest': 'some-digest',
        'KeyTag': 123,
        'Id': 'some-id'
    }])

    @model_validator(mode='after')
    def validate_registrar_name(self):
        """
        All .com .net and .org domains are registered by Amazon Registrar. All other domains are registered by Gandi
        """
        if not (self.domain_name.endswith('.com') or
                self.domain_name.endswith('.net') or
                self.domain_name.endswith('.org')):
            self.registrar_name = 'GANDISAS'
        return self

    @model_validator(mode='after')
    def validate_registrar_url(self):
        if self.registrar_name == 'GANDISAS':
            self.registrar_url = 'https://gandi.net'

        return self

    @field_serializer('creation_date', 'updated_date', 'expiration_date')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


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
                        duration_in_years: int,
                        auto_renew: bool,
                        admin_contact: Dict,
                        registrant_contact: Dict,
                        tech_contact: Dict,
                        private_protect_admin_contact: bool,
                        private_protect_registrant_contact: bool,
                        private_protect_tech_contact: bool,
                        ) -> Route53DomainsOperation:

        operation = Route53DomainsOperation(
            status='SUCCESSFUL',
            type_='REGISTER_DOMAIN',
            submitted_date=datetime.now(timezone.utc),
            domain_name=domain_name,
            message='',
            status_flag='PENDING_ACCEPTANCE',
            last_updated_date=datetime.now(timezone.utc)
        )

        self.operations[operation.id_] = operation

        domain = Route53Domain(
            domain_name=domain_name,
            auto_renew=auto_renew,
            admin_contact=Route53DomainsContactDetail.model_validate(admin_contact),
            registrant_contact=Route53DomainsContactDetail.model_validate(registrant_contact),
            tech_contact=Route53DomainsContactDetail.model_validate(tech_contact),
            admin_privacy=private_protect_admin_contact,
            registrant_privacy=private_protect_registrant_contact,
            tech_privacy=private_protect_tech_contact,
            expiration_date=datetime.now(timezone.utc) + timedelta(days=365*duration_in_years),
            status_list=['SUCCESSFUL'],
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
