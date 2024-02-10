from datetime import datetime, timezone, timedelta
from typing import Dict, List, Literal

import pydantic.alias_generators
from pydantic import (BaseModel as PydanticBaseModel,
                      Field,
                      model_validator,
                      field_validator,
                      field_serializer,
                      ConfigDict)

from moto.moto_api._internal import MotoRandom
from moto.core.base_backend import BaseBackend, BackendDict
from moto.core.common_models import BaseModel
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
AWS_SUPPORTED_TLDS = ['ac', 'academy', 'accountants', 'actor', 'adult', 'agency', 'airforce', 'apartments',
                      'associates', 'auction', 'audio', 'band', 'bargains', 'bet', 'bike', 'bingo', 'biz',
                      'black', 'blue', 'boutique', 'builders', 'business', 'buzz', 'cab', 'cafe', 'camera',
                      'camp', 'capital', 'cards', 'care', 'careers', 'cash', 'casino', 'catering', 'cc',
                      'center', 'ceo', 'chat', 'cheap', 'church', 'city', 'claims', 'cleaning', 'click',
                      'clinic', 'clothing', 'cloud', 'club', 'coach', 'codes', 'coffee', 'college', 'com',
                      'community', 'company', 'computer', 'condos', 'construction', 'consulting', 'contractors',
                      'cool', 'coupons', 'credit', 'creditcard', 'cruises', 'dance', 'dating', 'deals',
                      'degree', 'delivery', 'democrat', 'dental', 'diamonds', 'diet', 'digital', 'direct',
                      'directory', 'discount', 'dog', 'domains', 'education', 'email', 'energy', 'engineering',
                      'enterprises', 'equipment', 'estate', 'events', 'exchange', 'expert', 'exposed',
                      'express', 'fail', 'farm', 'finance', 'financial', 'fish', 'fitness', 'flights',
                      'florist', 'flowers', 'fm', 'football', 'forsale', 'foundation', 'fund', 'furniture',
                      'futbol', 'fyi', 'gallery', 'games', 'gift', 'gifts', 'gives', 'glass', 'global',
                      'gmbh', 'gold', 'golf', 'graphics', 'gratis', 'green', 'gripe', 'group', 'guide',
                      'guitars', 'guru', 'haus', 'healthcare', 'help', 'hiv', 'hockey', 'holdings', 'holiday',
                      'host', 'hosting', 'house', 'im', 'immo', 'immobilien', 'industries', 'info', 'ink',
                      'institute', 'insure', 'international', 'investments', 'io', 'irish', 'jewelry', 'juegos',
                      'kaufen', 'kim', 'kitchen', 'kiwi', 'land', 'lease', 'legal', 'lgbt', 'life',
                      'lighting', 'limited', 'limo', 'link', 'live', 'loan', 'loans', 'lol', 'maison',
                      'management', 'marketing', 'mba', 'media', 'memorial', 'mobi', 'moda', 'money',
                      'mortgage', 'movie', 'name', 'net', 'network', 'news', 'ninja', 'onl', 'online', 'org',
                      'partners', 'parts', 'photo', 'photography', 'photos', 'pics', 'pictures', 'pink',
                      'pizza', 'place', 'plumbing', 'plus', 'poker', 'porn', 'press', 'pro', 'productions',
                      'properties', 'property', 'pub', 'qpon', 'recipes', 'red', 'reise', 'reisen', 'rentals',
                      'repair', 'report', 'republican', 'restaurant', 'reviews', 'rip', 'rocks', 'run', 'sale',
                      'sarl', 'school', 'schule', 'services', 'sex', 'sexy', 'shiksha', 'shoes', 'show',
                      'singles', 'site', 'soccer', 'social', 'solar', 'solutions', 'space', 'store', 'studio',
                      'style', 'sucks', 'supplies', 'supply', 'support', 'surgery', 'systems', 'tattoo', 'tax',
                      'taxi', 'team', 'tech', 'technology', 'tennis', 'theater', 'tienda', 'tips', 'tires',
                      'today', 'tools', 'tours', 'town', 'toys', 'trade', 'training', 'tv', 'university',
                      'uno', 'vacations', 'vegas', 'ventures', 'vg', 'viajes', 'video', 'villas', 'vision',
                      'voyage', 'watch', 'website', 'wedding', 'wiki', 'wine', 'works', 'world', 'wtf', 'xyz',
                      'zone']

AWS_TLDS_REGEX_CAPTURE_GROUP = f'({'|'.join(AWS_SUPPORTED_TLDS)})'
AWS_ROUTE53_DOMAIN_REGEX = rf'^([a-z0-9\.-])+\.{AWS_TLDS_REGEX_CAPTURE_GROUP}$'


class CommonBaseModelMeta(type(PydanticBaseModel), type(BaseModel)):
    """
    In order to create classes that inherit both PydanticBaseModel and BaseModel we need a common parent metaclass
    to avoid a metaclass conflict between them
    """
    pass


class Route53DomainsOperation(PydanticBaseModel, BaseModel, metaclass=CommonBaseModelMeta):
    model_config = ConfigDict(alias_generator=pydantic.alias_generators.to_pascal)

    id_: str = Field(alias='OperationId', default_factory=lambda: str(MotoRandom().uuid4()))
    domain_name: str
    status: DomainOperationStatus
    type_: DomainOperationType = Field(alias='Type')
    message: str | None = None
    status_flag: DomainOperationStatusFlag
    submitted_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_serializer('submitted_date', 'last_updated_date')
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat()


class Route53DomainsContactDetail(PydanticBaseModel):
    model_config = ConfigDict(alias_generator=pydantic.alias_generators.to_pascal)

    address_line_1: str | None = Field(max_length=255, default=None)
    address_line_2: str | None = Field(max_length=255, default=None)
    city: str | None = Field(max_length=255, default=None)
    contact_type: DomainContactDetailContactType | None = None
    country_code: DomainContactDetailCountryCode | None = None
    email: str | None = Field(max_length=254, default=None)
    extra_params: List[Dict] | None = Field(alias='ExtraParams', default=None)
    fax: str | None = Field(pattern=r'\+[0-9]+\.[0-9]+', max_length=30, default=None)
    first_name: str | None = Field(max_length=255, default=None)
    last_name: str | None = Field(max_length=255, default=None)
    organization_name: str | None = Field(max_length=255, default=None)
    phone_number: str | None = Field(pattern=r'\+[0-9]+\.[0-9]+', default=None)
    state: str | None = Field(max_length=255, default=None)
    zip_code: str | None = Field(max_length=255, default=None)

    @model_validator(mode='after')
    def validate_contact_type(self):
        if self.contact_type != 'PERSON' and not self.organization_name:
            raise ValueError('Must specify OrganizationName when ContactType is not PERSON')
        return self


class NameServer(PydanticBaseModel):
    model_config = ConfigDict(alias_generator=pydantic.alias_generators.to_pascal)

    name: str
    glue_ips: List[str]


class Route53Domain(PydanticBaseModel, BaseModel, metaclass=CommonBaseModelMeta):
    model_config = ConfigDict(alias_generator=pydantic.alias_generators.to_pascal)

    domain_name: str = Field(pattern=AWS_ROUTE53_DOMAIN_REGEX)
    name_servers: List[NameServer] = [
        NameServer.model_validate({'Name': 'dns1.aws.amazon.com', 'GlueIps': ['1.1.1.1']})  # FIXME
    ]
    auto_renew: bool = True
    admin_contact: Route53DomainsContactDetail | None = None
    registrant_contact: Route53DomainsContactDetail | None = None
    tech_contact: Route53DomainsContactDetail | None = None
    admin_privacy: bool = True
    registrant_privacy: bool = True
    tech_privacy: bool = True
    registrar_name: str = 'AMAZON'
    whois_server: str = 'whois.iana.org'
    registrar_url: str = 'https://aws.amazon.com'
    abuse_contact_email: str = 'abuse@aws.com'
    abuse_contact_phone: str = '+11234567890'
    registry_domain_id: str | None = None  # Reserved for future use
    creation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expiration_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=365))
    reseller: str = 'Amazon'
    status_list: List[DomainOperationStatus] = []
    dns_sec_keys: List[Dict] = [{
        'Algorithm': 13,  # Always 13 for Route53 domains
        'Flags': 257,  # Code for KSK - Key Singing Key
        'PublicKey': 'some-public-key-in-base-64',
        'DigestType': 1,  # SHA1
        'Digest': 'some-digest',
        'KeyTag': 123,
        'Id': 'some-id'
    }]

    @field_validator('expiration_date')
    def validate_expiration_date(cls, v: datetime):
        duration_in_years = v - datetime.now(timezone.utc)
        if timedelta(days=365) <= duration_in_years <= timedelta(days=365*10):
            return v
        raise ValueError('Cannot register domain for a duration that is less than 1 year or more than 10 years')

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
            'StatusList': ['SUCCESSFUL']
        })

        operation = Route53DomainsOperation.model_validate({
            'DomainName': domain_name,
            'Status': 'SUCCESSFUL',
            'Type': 'REGISTER_DOMAIN',
            'StatusFlag': 'PENDING_ACCEPTANCE'
        })

        self.operations[operation.id_] = operation

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
