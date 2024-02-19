import re
from datetime import datetime, timezone, timedelta
from ipaddress import ip_address
from typing import Dict, List

from moto.core.common_models import BaseModel
from moto.moto_api._internal import MotoRandom

DOMAIN_OPERATION_STATUSES = ('SUBMITTED', 'IN_PROGRESS', 'ERROR', 'SUCCESSFUL', 'FAILED')

DOMAIN_OPERATION_TYPES = ('REGISTER_DOMAIN', 'DELETE_DOMAIN', 'TRANSFER_IN_DOMAIN', 'UPDATE_DOMAIN_CONTACT',
                          'UPDATE_NAMESERVER', 'CHANGE_PRIVACY_PROTECTION', 'DOMAIN_LOCK', 'ENABLE_AUTORENEW',
                          'DISABLE_AUTORENEW', 'ADD_DNSSEC', 'REMOVE_DNSSEC', 'EXPIRE_DOMAIN', 'TRANSFER_OUT_DOMAIN',
                          'CHANGE_DOMAIN_OWNER', 'RENEW_DOMAIN', 'PUSH_DOMAIN', 'INTERNAL_TRANSFER_OUT_DOMAIN',
                          'INTERNAL_TRANSFER_IN_DOMAIN')

DOMAIN_OPERATION_STATUS_FLAGS = ('PENDING_ACCEPTANCE', 'PENDING_CUSTOMER_ACTION', 'PENDING_AUTHORIZATION',
                                 'PENDING_PAYMENT_VERIFICATION', 'PENDING_SUPPORT_CASE')

DOMAIN_CONTACT_DETAIL_CONTACT_TYPES = ('PERSON', 'COMPANY', 'ASSOCIATION', 'PUBLIC_BODY', 'RESELLER', 'ORGANIZATION')

DOMAIN_CONTACT_DETAIL_COUNTRY_CODES = ('AC', 'AD', 'AE', 'AF', 'AG', 'AI', 'AL', 'AM', 'AN', 'AO', 'AQ', 'AR',  'AS',
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
                                       'YT', 'ZA', 'ZM', 'ZW')

# List of supported top-level domains that you can register with Amazon Route53
AWS_SUPPORTED_TLDS = ('ac', 'academy', 'accountants', 'actor', 'adult', 'agency', 'airforce', 'apartments',
                      'associates', 'auction', 'audio', 'band', 'bargains', 'bet', 'bike', 'bingo', 'biz', 'black',
                      'blue', 'boutique', 'builders', 'business', 'buzz', 'cab', 'cafe', 'camera', 'camp', 'capital',
                      'cards', 'care', 'careers', 'cash', 'casino', 'catering', 'cc', 'center', 'ceo', 'chat', 'cheap',
                      'church', 'city', 'claims', 'cleaning', 'click', 'clinic', 'clothing', 'cloud', 'club', 'coach',
                      'codes', 'coffee', 'college', 'com', 'community', 'company', 'computer', 'condos', 'construction',
                      'consulting', 'contractors', 'cool', 'coupons', 'credit', 'creditcard', 'cruises', 'dance',
                      'dating', 'deals', 'degree', 'delivery', 'democrat', 'dental', 'diamonds', 'diet', 'digital',
                      'direct', 'directory', 'discount', 'dog', 'domains', 'education', 'email', 'energy',
                      'engineering', 'enterprises', 'equipment', 'estate', 'events', 'exchange', 'expert', 'exposed',
                      'express', 'fail', 'farm', 'finance', 'financial', 'fish', 'fitness', 'flights', 'florist',
                      'flowers', 'fm', 'football', 'forsale', 'foundation', 'fund', 'furniture', 'futbol', 'fyi',
                      'gallery', 'games', 'gift', 'gifts', 'gives', 'glass', 'global', 'gmbh', 'gold', 'golf',
                      'graphics', 'gratis', 'green', 'gripe', 'group', 'guide', 'guitars', 'guru', 'haus', 'healthcare',
                      'help', 'hiv', 'hockey', 'holdings', 'holiday', 'host', 'hosting', 'house', 'im', 'immo',
                      'immobilien', 'industries', 'info', 'ink', 'institute', 'insure', 'international', 'investments',
                      'io', 'irish', 'jewelry', 'juegos', 'kaufen', 'kim', 'kitchen', 'kiwi', 'land', 'lease', 'legal',
                      'lgbt', 'life', 'lighting', 'limited', 'limo', 'link', 'live', 'loan', 'loans', 'lol', 'maison',
                      'management', 'marketing', 'mba', 'media', 'memorial', 'mobi', 'moda', 'money', 'mortgage',
                      'movie', 'name', 'net', 'network', 'news', 'ninja', 'onl', 'online', 'org', 'partners', 'parts',
                      'photo', 'photography', 'photos', 'pics', 'pictures', 'pink', 'pizza', 'place', 'plumbing',
                      'plus', 'poker', 'porn', 'press', 'pro', 'productions', 'properties', 'property', 'pub', 'qpon',
                      'recipes', 'red', 'reise', 'reisen', 'rentals', 'repair', 'report', 'republican', 'restaurant',
                      'reviews', 'rip', 'rocks', 'run', 'sale', 'sarl', 'school', 'schule', 'services', 'sex', 'sexy',
                      'shiksha', 'shoes', 'show', 'singles', 'site', 'soccer', 'social', 'solar', 'solutions', 'space',
                      'store', 'studio', 'style', 'sucks', 'supplies', 'supply', 'support', 'surgery', 'systems',
                      'tattoo', 'tax', 'taxi', 'team', 'tech', 'technology', 'tennis', 'theater', 'tienda', 'tips',
                      'tires', 'today', 'tools', 'tours', 'town', 'toys', 'trade', 'training', 'tv', 'university',
                      'uno', 'vacations', 'vegas', 'ventures', 'vg', 'viajes', 'video', 'villas', 'vision', 'voyage',
                      'watch', 'website', 'wedding', 'wiki', 'wine', 'works', 'world', 'wtf', 'xyz', 'zone')

AWS_TLDS_REGEX_CAPTURE_GROUP = f'({'|'.join(AWS_SUPPORTED_TLDS)})'
AWS_ROUTE53_VALID_DOMAIN_REGEX = rf'^([a-z0-9\.-])+\.{AWS_TLDS_REGEX_CAPTURE_GROUP}$'
PHONE_NUMBER_REGEX = r'\+\d*\.\d{10}$'


class ValidationException(Exception):
    def __init__(self, errors: List[str]):
        super().__init__('\n\t'.join(errors))
        self.errors = errors


class Route53DomainsOperation(BaseModel):
    def __init__(self,
                 id_: str,
                 domain_name: str,
                 status: str,
                 type_: str,
                 submitted_date: datetime,
                 last_updated_date: datetime,
                 message: str | None = None,
                 status_flag: str | None = None,
                 ):
        self.id = id_
        self.domain_name = domain_name
        self.status = status
        self.type = type_
        self.submitted_date = submitted_date
        self.last_updated_date = last_updated_date
        self.message = message
        self.status_flag = status_flag

    @classmethod
    def validate(cls,
                 domain_name: str,
                 status: str,
                 type_: str,
                 message: str | None = None,
                 status_flag: str | None = None):

        id_ = str(MotoRandom().uuid4())
        submitted_date = datetime.now(timezone.utc)
        last_updated_date = datetime.now(timezone.utc)

        return cls(id_,
                   domain_name,
                   status,
                   type_,
                   submitted_date,
                   last_updated_date,
                   message,
                   status_flag)

    def to_serializable_dict(self) -> Dict:
        d = {
            'OperationId': self.id,
            'DomainName': self.domain_name,
            'LastUpdatedDate': self.last_updated_date.isoformat(),
            'StatusFlag': self.status_flag,
            'SubmittedDate': self.submitted_date.isoformat(),
            'Type': self.type
        }

        if self.message:
            d['Message'] = self.message

        return d


class Route53DomainsContactDetail(BaseModel):
    def __init__(self,
                 address_line_1: str | None,
                 address_line_2: str | None,
                 city: str | None,
                 contact_type: str | None,
                 country_code: str | None,
                 email: str | None,
                 extra_params: List[Dict] | None,
                 fax: str | None,
                 first_name: str | None,
                 last_name: str | None,
                 organization_name: str | None,
                 phone_number: str | None,
                 state: str | None,
                 zip_code: str | None):
        super().__init__()
        self.address_line_1 = address_line_1
        self.address_line_2 = address_line_2
        self.city = city
        self.contact_type = contact_type
        self.country_code = country_code
        self.email = email
        self.extra_params = extra_params
        self.fax = fax
        self.first_name = first_name
        self.last_name = last_name
        self.organization_name = organization_name
        self.phone_number = phone_number
        self.state = state
        self.zip_code = zip_code

    @classmethod
    def validate(cls,
                 address_line_1: str | None,
                 address_line_2: str | None,
                 city: str | None,
                 contact_type: str | None,
                 country_code: str | None,
                 email: str | None,
                 extra_params: List[Dict] | None,
                 fax: str | None,
                 first_name: str | None,
                 last_name: str | None,
                 organization_name: str | None,
                 phone_number: str | None,
                 state: str | None,
                 zip_code: str | None):
        errors = []

        cls.__validate_str_len(address_line_1, 'AddressLine1', 255, errors)
        cls.__validate_str_len(address_line_2, 'AddressLine2', 255, errors)
        cls.__validate_str_len(city, 'City', 255, errors)
        cls.__validate_str_len(email, 'Email', 255, errors)
        cls.__validate_str_len(fax, 'Fax', 255, errors)
        cls.__validate_str_len(first_name, 'FirstName', 255, errors)
        cls.__validate_str_len(last_name, 'LastName', 255, errors)
        cls.__validate_str_len(state, 'State', 255, errors)
        cls.__validate_str_len(zip_code, 'ZipCode', 255, errors)

        if contact_type:
            if contact_type not in DOMAIN_CONTACT_DETAIL_CONTACT_TYPES:
                errors.append(f'Invalid contact type {contact_type}')
            else:
                if contact_type != 'PERSON' and not organization_name:
                    errors.append('Must supply OrganizationName when ContactType is not PERSON')

        if country_code and country_code not in DOMAIN_CONTACT_DETAIL_COUNTRY_CODES:
            errors.append(f'CountryCode {country_code} is invalid')

        if phone_number and not re.match(PHONE_NUMBER_REGEX, phone_number):
            errors.append('PhoneNumber is in an invalid format')

        if errors:
            raise ValidationException(errors)

        return cls(address_line_1,
                   address_line_2,
                   city,
                   contact_type,
                   country_code,
                   email,
                   extra_params,
                   fax,
                   first_name,
                   last_name,
                   organization_name,
                   phone_number,
                   state,
                   zip_code)

    @classmethod
    def validate_dict(cls, d: Dict):
        address_line_1: str = d.get('AddressLine1')
        address_line_2: str = d.get('AddressLine2')
        city: str = d.get('City')
        contact_type: str = d.get('ContactType')
        country_code: str = d.get('CountryCode')
        email: str = d.get('Email')
        extra_params: List[Dict] = d.get('ExtraParams')
        fax: str = d.get('Fax')
        first_name: str = d.get('FirstName')
        last_name: str = d.get('LastName')
        organization_name: str = d.get('OrganizationName')
        phone_number: str = d.get('PhoneNumber')
        state: str = d.get('State')
        zip_code: str = d.get('ZipCode')
        return cls.validate(
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            contact_type=contact_type,
            country_code=country_code,
            email=email,
            extra_params=extra_params,
            fax=fax,
            first_name=first_name,
            last_name=last_name,
            organization_name=organization_name,
            phone_number=phone_number,
            state=state,
            zip_code=zip_code
        )

    @staticmethod
    def __validate_str_len(value: str, field_name: str, max_len: int, errors: List[str]):
        if value and len(value) > max_len:
            errors.append(f'Length of {field_name} is more than {max_len}')

    def to_serializable_dict(self) -> Dict:
        d = {
            'FirstName': self.first_name,
            'LastName': self.last_name,
            'ContactType': self.contact_type,
            'OrganizationName': self.organization_name,
            'AddressLine1': self.address_line_1,
            'AddressLine2': self.address_line_2,
            'City': self.city,
            'State': self.state,
            'CountryCode': self.country_code,
            'ZipCode': self.zip_code,
            'PhoneNumber': self.phone_number,
            'Email': self.email,
            'Fax': self.fax,
            'ExtraParams': self.extra_params
        }

        for key in d:
            if d[key] is None:
                del d[key]

        return d


class NameServer:
    def __init__(self, name: str, glue_ips: List[str]):
        self.name = name
        self.glue_ips = glue_ips

    @classmethod
    def validate(cls, name: str, glue_ips: List[str] | None = None):
        glue_ips = glue_ips or []
        errors = []

        if not name:
            errors.append(f'{name} is not a valid DNS nameserver')

        for ip in glue_ips:
            try:
                ip_address(ip)
            except ValueError:
                errors.append(f'{ip} is not a valid IP address')

        if errors:
            raise ValidationException(errors)

        return cls(name, glue_ips)

    @classmethod
    def validate_dict(cls, d: Dict):
        name = d.get('Name')
        glue_ips = d.get('GlueIPs')
        return cls.validate(name, glue_ips)

    def to_serializable_dict(self) -> Dict:
        return {
            'Name': self.name,
            'GlueIps': self.glue_ips
        }


class Route53Domain(BaseModel):

    def __init__(self,
                 domain_name: str,
                 name_servers: List[NameServer],
                 auto_renew: bool,
                 admin_contact: Route53DomainsContactDetail,
                 registrant_contact: Route53DomainsContactDetail,
                 tech_contact: Route53DomainsContactDetail,
                 admin_privacy: bool,
                 registrant_privacy: bool,
                 tech_privacy: bool,
                 registrar_name: str,
                 whois_server: str,
                 registrar_url: str,
                 abuse_contact_email: str,
                 abuse_contact_phone: str,
                 registry_domain_id: str,
                 creation_date: datetime,
                 updated_date: datetime,
                 expiration_date: datetime,
                 reseller: str,
                 status_list: List[str],
                 dns_sec_keys: List[Dict],
                 extra_params: List[Dict]
                 ):
        self.domain_name = domain_name
        self.name_servers = name_servers
        self.auto_renew = auto_renew
        self.admin_contact = admin_contact
        self.registrant_contact = registrant_contact
        self.tech_contact = tech_contact
        self.admin_privacy = admin_privacy
        self.registrant_privacy = registrant_privacy
        self.tech_privacy = tech_privacy
        self.registrar_name = registrar_name
        self.whois_server = whois_server
        self.registrar_url = registrar_url
        self.abuse_contact_email = abuse_contact_email
        self.abuse_contact_phone = abuse_contact_phone
        self.registry_domain_id = registry_domain_id
        self.creation_date = creation_date
        self.updated_date = updated_date
        self.expiration_date = expiration_date
        self.reseller = reseller
        self.status_list = status_list
        self.dns_sec_keys = dns_sec_keys
        self.extra_params = extra_params

    @classmethod
    def validate(cls,
                 domain_name: str,
                 admin_contact: Route53DomainsContactDetail,
                 registrant_contact: Route53DomainsContactDetail,
                 tech_contact: Route53DomainsContactDetail,
                 name_servers: List[Dict] | None = None,
                 auto_renew: bool = True,
                 admin_privacy: bool = True,
                 registrant_privacy: bool = True,
                 tech_privacy: bool = True,
                 registrar_name: str | None = None,
                 whois_server: str | None = None,
                 registrar_url: str | None = None,
                 abuse_contact_email: str | None = None,
                 abuse_contact_phone: str | None = None,
                 registry_domain_id: str | None = None,
                 expiration_date: datetime | None = None,
                 reseller: str | None = None,
                 dns_sec_keys: List[Dict] | None = None,
                 extra_params: List[Dict] | None = None
                 ):
        errors = []

        cls.__validate_domain_name(domain_name, errors)

        name_servers = name_servers or []
        try:
            name_servers = [NameServer.validate_dict(name_server) for name_server in name_servers] or \
                           [NameServer.validate(name='ns-2048.awscdn-64.net'),
                            NameServer.validate(name='ns-2051.awscdn-67.net'),
                            NameServer.validate(name='ns-2050.awscdn-66.net'),
                            NameServer.validate(name='ns-2049.awscdn-65.net'),]
        except ValidationException as e:
            errors += e.errors

        creation_date = datetime.now(timezone.utc)
        updated_date = datetime.now(timezone.utc)
        expiration_date = expiration_date or datetime.now(timezone.utc) + timedelta(days=365*10)
        registrar_name = registrar_name or 'GANDI SAS'
        whois_server = whois_server or 'whois.gandi.net'
        registrar_url = registrar_url or 'http://www.gandi.net'
        abuse_contact_email = abuse_contact_email or 'abuse@support.gandi.net'
        status_list = ['SUCCEEDED']

        time_until_expiration = expiration_date - datetime.now(timezone.utc)
        if time_until_expiration < timedelta(days=365) or time_until_expiration > timedelta(days=365*10):
            errors.append('ExpirationDate must by between 1 and 10 years from now')

        if errors:
            raise ValidationException(errors)

        return cls(
            domain_name=domain_name,
            name_servers=name_servers,
            auto_renew=auto_renew,
            admin_contact=admin_contact,
            registrant_contact=registrant_contact,
            tech_contact=tech_contact,
            admin_privacy=admin_privacy,
            registrant_privacy=registrant_privacy,
            tech_privacy=tech_privacy,
            registrar_name=registrar_name,
            whois_server=whois_server,
            registrar_url=registrar_url,
            abuse_contact_email=abuse_contact_email,
            abuse_contact_phone=abuse_contact_phone,
            registry_domain_id=registry_domain_id,
            creation_date=creation_date,
            updated_date=updated_date,
            expiration_date=expiration_date,
            reseller=reseller,
            status_list=status_list,
            dns_sec_keys=dns_sec_keys,
            extra_params=extra_params
        )

    @staticmethod
    def __validate_domain_name(domain_name: str, errors: List[str]):
        tld = domain_name.split('.')[-1]
        if not tld:
            errors.append('Invalid domain name')
            return

        if tld not in AWS_SUPPORTED_TLDS:
            errors.append(f'TLD {tld} is not supported in AWS')
            return

        if not re.match(AWS_ROUTE53_VALID_DOMAIN_REGEX, domain_name):
            errors.append('Invalid domain name')
            return

    def to_serializable_dict(self):
        return {
            'DomainName': self.domain_name,
            'NameServers': [name_server.to_serializable_dict() for name_server in self.name_servers],
            'AutoRenew': self.auto_renew,
            'AdminContact': self.admin_contact.to_serializable_dict(),
            'RegistrantContact': self.registrant_contact.to_serializable_dict(),
            'TechContact': self.tech_contact.to_serializable_dict(),
            'AdminPrivacy': self.admin_privacy,
            'RegistrantPrivacy': self.registrant_privacy,
            'TechPrivacy': self.tech_privacy,
            'RegistrarName': self.registrar_name,
            'WhoIsServer': self.whois_server,
            'RegistrarUrl': self.registrar_url,
            'AbuseContactEmail': self.abuse_contact_email,
            'AbuseContactPhone': self.abuse_contact_phone,
            'RegistryDomainId': '',
            'CreationDate': self.creation_date.isoformat(),
            'UpdateDate': self.updated_date.isoformat(),
            'ExpirationDate': self.expiration_date.isoformat(),
            'Reseller': self.reseller,
            'DnsSec': '',
            'StatusList': self.status_list,
            'DnsSecKeys': self.dns_sec_keys,
            'BillingContact': self.admin_contact.to_serializable_dict()
        }
