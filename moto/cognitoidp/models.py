import datetime
import hashlib
import json
import os
import time
import uuid
import enum
import random
from boto3 import Session
from jose import jws
from collections import OrderedDict
from moto.core import BaseBackend, BaseModel
from moto.core import ACCOUNT_ID as DEFAULT_ACCOUNT_ID
from .exceptions import (
    GroupExistsException,
    NotAuthorizedError,
    ResourceNotFoundError,
    UserNotFoundError,
    UsernameExistsException,
    UserNotConfirmedException,
    InvalidParameterException,
    ExpiredCodeException,
)
from .utils import (
    create_id,
    check_secret_hash,
    validate_username_format,
    flatten_attrs,
    expand_attrs,
    PAGINATION_MODEL,
)
from moto.utilities.paginator import paginate


class UserStatus(str, enum.Enum):
    FORCE_CHANGE_PASSWORD = "FORCE_CHANGE_PASSWORD"
    CONFIRMED = "CONFIRMED"
    UNCONFIRMED = "UNCONFIRMED"
    RESET_REQUIRED = "RESET_REQUIRED"


class CognitoIdpUserPoolAttribute(BaseModel):

    STANDARD_SCHEMA = {
        "sub": {
            "AttributeDataType": "String",
            "Mutable": False,
            "Required": True,
            "StringAttributeConstraints": {"MinLength": "1", "MaxLength": "2048"},
        },
        "name": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "given_name": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "family_name": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "middle_name": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "nickname": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "preferred_username": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "profile": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "picture": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "website": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "email": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "email_verified": {
            "AttributeDataType": "Boolean",
            "Mutable": True,
            "Required": False,
        },
        "gender": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "birthdate": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "10", "MaxLength": "10"},
        },
        "zoneinfo": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "locale": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "phone_number": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "phone_number_verified": {
            "AttributeDataType": "Boolean",
            "Mutable": True,
            "Required": False,
        },
        "address": {
            "AttributeDataType": "String",
            "Mutable": True,
            "Required": False,
            "StringAttributeConstraints": {"MinLength": "0", "MaxLength": "2048"},
        },
        "updated_at": {
            "AttributeDataType": "Number",
            "Mutable": True,
            "Required": False,
            "NumberAttributeConstraints": {"MinValue": "0"},
        },
    }

    ATTRIBUTE_DATA_TYPES = {"Boolean", "DateTime", "String", "Number"}

    def __init__(self, name, custom, schema):
        self.name = name
        self.custom = custom
        attribute_data_type = schema.get("AttributeDataType", None)
        if (
            attribute_data_type
            and attribute_data_type
            not in CognitoIdpUserPoolAttribute.ATTRIBUTE_DATA_TYPES
        ):
            raise InvalidParameterException(
                f"Validation error detected: Value '{attribute_data_type}' failed to satisfy constraint: Member must satisfy enum value set: [Boolean, Number, String, DateTime]"
            )

        if self.custom:
            self._init_custom(schema)
        else:
            self._init_standard(schema)

    def _init_custom(self, schema):
        self.name = "custom:" + self.name
        attribute_data_type = schema.get("AttributeDataType", None)
        if not attribute_data_type:
            raise InvalidParameterException(
                "Invalid AttributeDataType input, consider using the provided AttributeDataType enum."
            )
        self.data_type = attribute_data_type
        self.developer_only = schema.get("DeveloperOnlyAttribute", False)
        if self.developer_only:
            self.name = "dev:" + self.name
        self.mutable = schema.get("Mutable", True)
        if schema.get("Required", False):
            raise InvalidParameterException(
                "Required custom attributes are not supported currently."
            )
        self.required = False
        self._init_constraints(schema, None)

    def _init_standard(self, schema):
        attribute_data_type = schema.get("AttributeDataType", None)
        default_attribute_data_type = CognitoIdpUserPoolAttribute.STANDARD_SCHEMA[
            self.name
        ]["AttributeDataType"]
        if attribute_data_type and attribute_data_type != default_attribute_data_type:
            raise InvalidParameterException(
                f"You can not change AttributeDataType or set developerOnlyAttribute for standard schema attribute {self.name}"
            )
        self.data_type = default_attribute_data_type
        if schema.get("DeveloperOnlyAttribute", False):
            raise InvalidParameterException(
                f"You can not change AttributeDataType or set developerOnlyAttribute for standard schema attribute {self.name}"
            )
        else:
            self.developer_only = False
        self.mutable = schema.get(
            "Mutable",
            CognitoIdpUserPoolAttribute.STANDARD_SCHEMA[self.name]["Mutable"],
        )
        self.required = schema.get(
            "Required",
            CognitoIdpUserPoolAttribute.STANDARD_SCHEMA[self.name]["Required"],
        )
        constraints_key = None
        if self.data_type == "Number":
            constraints_key = "NumberAttributeConstraints"
        elif self.data_type == "String":
            constraints_key = "StringAttributeConstraints"
        default_constraints = (
            None
            if not constraints_key
            else CognitoIdpUserPoolAttribute.STANDARD_SCHEMA[self.name][constraints_key]
        )
        self._init_constraints(schema, default_constraints)

    def _init_constraints(self, schema, default_constraints):
        def numeric_limit(num, constraint_type):
            if not num:
                return
            parsed = None
            try:
                parsed = int(num)
            except ValueError:
                pass
            if parsed is None or parsed < 0:
                raise InvalidParameterException(
                    f"Invalid {constraint_type} for schema attribute {self.name}"
                )
            return parsed

        self.string_constraints = None
        self.number_constraints = None

        if "AttributeDataType" in schema:
            # Quirk - schema is set/validated only if AttributeDataType is specified
            if self.data_type == "String":
                string_constraints = schema.get(
                    "StringAttributeConstraints", default_constraints
                )
                if not string_constraints:
                    return
                min_len = numeric_limit(
                    string_constraints.get("MinLength", None),
                    "StringAttributeConstraints",
                )
                max_len = numeric_limit(
                    string_constraints.get("MaxLength", None),
                    "StringAttributeConstraints",
                )
                if (min_len and min_len > 2048) or (max_len and max_len > 2048):
                    raise InvalidParameterException(
                        f"user.{self.name}: String attributes cannot have a length of more than 2048"
                    )
                if min_len and max_len and min_len > max_len:
                    raise InvalidParameterException(
                        f"user.{self.name}: Max length cannot be less than min length."
                    )
                self.string_constraints = string_constraints
            elif self.data_type == "Number":
                number_constraints = schema.get(
                    "NumberAttributeConstraints", default_constraints
                )
                if not number_constraints:
                    return
                # No limits on either min or max value
                min_val = numeric_limit(
                    number_constraints.get("MinValue", None),
                    "NumberAttributeConstraints",
                )
                max_val = numeric_limit(
                    number_constraints.get("MaxValue", None),
                    "NumberAttributeConstraints",
                )
                if min_val and max_val and min_val > max_val:
                    raise InvalidParameterException(
                        f"user.{self.name}: Max value cannot be less than min value."
                    )
                self.number_constraints = number_constraints

    def to_json(self):
        return {
            "Name": self.name,
            "AttributeDataType": self.data_type,
            "DeveloperOnlyAttribute": self.developer_only,
            "Mutable": self.mutable,
            "Required": self.required,
            "NumberAttributeConstraints": self.number_constraints,
            "StringAttributeConstraints": self.string_constraints,
        }


class CognitoIdpUserPool(BaseModel):
    def __init__(self, region, name, extended_config):
        self.region = region
        self.id = "{}_{}".format(self.region, str(uuid.uuid4().hex))
        self.arn = "arn:aws:cognito-idp:{}:{}:userpool/{}".format(
            self.region, DEFAULT_ACCOUNT_ID, self.id
        )
        self.name = name
        self.status = None
        self.extended_config = extended_config or {}
        self.creation_date = datetime.datetime.utcnow()
        self.last_modified_date = datetime.datetime.utcnow()

        self.mfa_config = "OFF"
        self.sms_mfa_config = None
        self.token_mfa_config = None

        self.schema_attributes = {}
        for schema in extended_config.pop("Schema", {}):
            attribute = CognitoIdpUserPoolAttribute(
                schema["Name"],
                schema["Name"] not in CognitoIdpUserPoolAttribute.STANDARD_SCHEMA,
                schema,
            )
            self.schema_attributes[attribute.name] = attribute
        for (
            standard_attribute_name,
            standard_attribute_schema,
        ) in CognitoIdpUserPoolAttribute.STANDARD_SCHEMA.items():
            if standard_attribute_name not in self.schema_attributes:
                self.schema_attributes[
                    standard_attribute_name
                ] = CognitoIdpUserPoolAttribute(
                    standard_attribute_name, False, standard_attribute_schema
                )

        self.clients = OrderedDict()
        self.identity_providers = OrderedDict()
        self.groups = OrderedDict()
        self.users = OrderedDict()
        self.resource_servers = OrderedDict()
        self.refresh_tokens = {}
        self.access_tokens = {}
        self.id_tokens = {}

        with open(
            os.path.join(os.path.dirname(__file__), "resources/jwks-private.json")
        ) as f:
            self.json_web_key = json.loads(f.read())

    def _account_recovery_setting(self):
        # AccountRecoverySetting is not present in DescribeUserPool response if the pool was created without
        # specifying it, ForgotPassword works on default settings nonetheless
        return self.extended_config.get(
            "AccountRecoverySetting",
            {
                "RecoveryMechanisms": [
                    {"Priority": 1, "Name": "verified_phone_number"},
                    {"Priority": 2, "Name": "verified_email"},
                ]
            },
        )

    def _base_json(self):
        return {
            "Id": self.id,
            "Arn": self.arn,
            "Name": self.name,
            "Status": self.status,
            "CreationDate": time.mktime(self.creation_date.timetuple()),
            "LastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
            "MfaConfiguration": self.mfa_config,
            "EstimatedNumberOfUsers": len(self.users),
        }

    def to_json(self, extended=False):
        user_pool_json = self._base_json()
        if extended:
            user_pool_json.update(self.extended_config)
            user_pool_json.update(
                {
                    "SchemaAttributes": [
                        att.to_json() for att in self.schema_attributes.values()
                    ]
                }
            )
        else:
            user_pool_json["LambdaConfig"] = (
                self.extended_config.get("LambdaConfig") or {}
            )

        return user_pool_json

    def _get_user(self, username):
        """Find a user within a user pool by Username or any UsernameAttributes
        (`email` or `phone_number` or both)"""
        if self.extended_config.get("UsernameAttributes"):
            attribute_types = self.extended_config["UsernameAttributes"]
            for user in self.users.values():
                if username in [
                    flatten_attrs(user.attributes).get(attribute_type)
                    for attribute_type in attribute_types
                ]:
                    return user

        return self.users.get(username)

    def create_jwt(
        self, client_id, username, token_use, expires_in=60 * 60, extra_data=None
    ):
        now = int(time.time())
        payload = {
            "iss": "https://cognito-idp.{}.amazonaws.com/{}".format(
                self.region, self.id
            ),
            "sub": self._get_user(username).id,
            "aud": client_id,
            "token_use": token_use,
            "auth_time": now,
            "exp": now + expires_in,
            "email": flatten_attrs(self._get_user(username).attributes).get("email"),
        }
        payload.update(extra_data or {})
        headers = {"kid": "dummy"}  # KID as present in jwks-public.json

        return (
            jws.sign(payload, self.json_web_key, headers, algorithm="RS256"),
            expires_in,
        )

    def add_custom_attributes(self, custom_attributes):
        attributes = []
        for attribute_schema in custom_attributes:
            base_name = attribute_schema["Name"]
            target_name = "custom:" + base_name
            if attribute_schema.get("DeveloperOnlyAttribute", False):
                target_name = "dev:" + target_name
            if target_name in self.schema_attributes:
                raise InvalidParameterException(
                    f"custom:{base_name}: Existing attribute already has name {target_name}."
                )
            attribute = CognitoIdpUserPoolAttribute(base_name, True, attribute_schema)
            attributes.append(attribute)
        for attribute in attributes:
            self.schema_attributes[attribute.name] = attribute

    def create_id_token(self, client_id, username):
        extra_data = self.get_user_extra_data_by_client_id(client_id, username)
        id_token, expires_in = self.create_jwt(
            client_id, username, "id", extra_data=extra_data
        )
        self.id_tokens[id_token] = (client_id, username)
        return id_token, expires_in

    def create_refresh_token(self, client_id, username):
        refresh_token = str(uuid.uuid4())
        self.refresh_tokens[refresh_token] = (client_id, username)
        return refresh_token

    def create_access_token(self, client_id, username):
        extra_data = {}
        user = self._get_user(username)
        if len(user.groups) > 0:
            extra_data["cognito:groups"] = [group.group_name for group in user.groups]

        access_token, expires_in = self.create_jwt(
            client_id, username, "access", extra_data=extra_data
        )
        self.access_tokens[access_token] = (client_id, username)
        return access_token, expires_in

    def create_tokens_from_refresh_token(self, refresh_token):
        client_id, username = self.refresh_tokens.get(refresh_token)
        if not username:
            raise NotAuthorizedError(refresh_token)

        access_token, expires_in = self.create_access_token(client_id, username)
        id_token, _ = self.create_id_token(client_id, username)
        return access_token, id_token, expires_in

    def get_user_extra_data_by_client_id(self, client_id, username):
        extra_data = {}
        current_client = self.clients.get(client_id, None)
        if current_client:
            for readable_field in current_client.get_readable_fields():
                attribute = list(
                    filter(
                        lambda f: f["Name"] == readable_field,
                        self._get_user(username).attributes,
                    )
                )
                if len(attribute) > 0:
                    extra_data.update({attribute[0]["Name"]: attribute[0]["Value"]})
        return extra_data


class CognitoIdpUserPoolDomain(BaseModel):
    def __init__(self, user_pool_id, domain, custom_domain_config=None):
        self.user_pool_id = user_pool_id
        self.domain = domain
        self.custom_domain_config = custom_domain_config or {}

    def _distribution_name(self):
        if self.custom_domain_config and "CertificateArn" in self.custom_domain_config:
            unique_hash = hashlib.md5(
                self.custom_domain_config["CertificateArn"].encode("utf-8")
            ).hexdigest()
            return f"{unique_hash[:16]}.cloudfront.net"
        unique_hash = hashlib.md5(self.user_pool_id.encode("utf-8")).hexdigest()
        return f"{unique_hash[:16]}.amazoncognito.com"

    def to_json(self, extended=True):
        distribution = self._distribution_name()
        if extended:
            return {
                "UserPoolId": self.user_pool_id,
                "AWSAccountId": str(uuid.uuid4()),
                "CloudFrontDistribution": distribution,
                "Domain": self.domain,
                "S3Bucket": None,
                "Status": "ACTIVE",
                "Version": None,
            }
        elif distribution:
            return {"CloudFrontDomain": distribution}
        return None


class CognitoIdpUserPoolClient(BaseModel):
    def __init__(self, user_pool_id, generate_secret, extended_config):
        self.user_pool_id = user_pool_id
        self.id = create_id()
        self.secret = str(uuid.uuid4())
        self.generate_secret = generate_secret or False
        self.extended_config = extended_config or {}

    def _base_json(self):
        return {
            "ClientId": self.id,
            "ClientName": self.extended_config.get("ClientName"),
            "UserPoolId": self.user_pool_id,
        }

    def to_json(self, extended=False):
        user_pool_client_json = self._base_json()
        if self.generate_secret:
            user_pool_client_json.update({"ClientSecret": self.secret})
        if extended:
            user_pool_client_json.update(self.extended_config)

        return user_pool_client_json

    def get_readable_fields(self):
        return self.extended_config.get("ReadAttributes", [])


class CognitoIdpIdentityProvider(BaseModel):
    def __init__(self, name, extended_config):
        self.name = name
        self.extended_config = extended_config or {}
        self.creation_date = datetime.datetime.utcnow()
        self.last_modified_date = datetime.datetime.utcnow()

    def _base_json(self):
        return {
            "ProviderName": self.name,
            "ProviderType": self.extended_config.get("ProviderType"),
            "CreationDate": time.mktime(self.creation_date.timetuple()),
            "LastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
        }

    def to_json(self, extended=False):
        identity_provider_json = self._base_json()
        if extended:
            identity_provider_json.update(self.extended_config)

        return identity_provider_json


class CognitoIdpGroup(BaseModel):
    def __init__(self, user_pool_id, group_name, description, role_arn, precedence):
        self.user_pool_id = user_pool_id
        self.group_name = group_name
        self.description = description or ""
        self.role_arn = role_arn
        self.precedence = precedence
        self.last_modified_date = datetime.datetime.now()
        self.creation_date = self.last_modified_date

        # Users who are members of this group.
        # Note that these links are bidirectional.
        self.users = set()

    def to_json(self):
        return {
            "GroupName": self.group_name,
            "UserPoolId": self.user_pool_id,
            "Description": self.description,
            "RoleArn": self.role_arn,
            "Precedence": self.precedence,
            "LastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
            "CreationDate": time.mktime(self.creation_date.timetuple()),
        }


class CognitoIdpUser(BaseModel):
    def __init__(self, user_pool_id, username, password, status, attributes):
        self.id = str(uuid.uuid4())
        self.user_pool_id = user_pool_id
        # Username is None when users sign up with an email or phone_number,
        # and should be given the value of the internal id generate (sub)
        self.username = username if username else self.id
        self.password = password
        self.status = status
        self.enabled = True
        self.attributes = attributes
        self.attribute_lookup = flatten_attrs(attributes)
        self.create_date = datetime.datetime.utcnow()
        self.last_modified_date = datetime.datetime.utcnow()
        self.sms_mfa_enabled = False
        self.software_token_mfa_enabled = False
        self.token_verified = False
        self.confirmation_code = None

        # Groups this user is a member of.
        # Note that these links are bidirectional.
        self.groups = set()

        self.update_attributes([{"Name": "sub", "Value": self.id}])

    def _base_json(self):
        return {
            "UserPoolId": self.user_pool_id,
            "Username": self.username,
            "UserStatus": self.status,
            "UserCreateDate": time.mktime(self.create_date.timetuple()),
            "UserLastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
        }

    # list_users brings back "Attributes" while admin_get_user brings back "UserAttributes".
    def to_json(
        self, extended=False, attributes_key="Attributes", attributes_to_get=None
    ):
        user_mfa_setting_list = []
        if self.software_token_mfa_enabled:
            user_mfa_setting_list.append("SOFTWARE_TOKEN_MFA")
        elif self.sms_mfa_enabled:
            user_mfa_setting_list.append("SMS_MFA")
        user_json = self._base_json()
        if extended:
            attrs = [
                attr
                for attr in self.attributes
                if not attributes_to_get or attr["Name"] in attributes_to_get
            ]
            user_json.update(
                {
                    "Enabled": self.enabled,
                    attributes_key: attrs,
                    "MFAOptions": [],
                    "UserMFASettingList": user_mfa_setting_list,
                }
            )

        return user_json

    def update_attributes(self, new_attributes):
        flat_attributes = flatten_attrs(self.attributes)
        flat_attributes.update(flatten_attrs(new_attributes))
        self.attribute_lookup = flat_attributes
        self.attributes = expand_attrs(flat_attributes)

    def delete_attributes(self, attrs_to_delete):
        flat_attributes = flatten_attrs(self.attributes)
        wrong_attrs = []
        for attr in attrs_to_delete:
            try:
                flat_attributes.pop(attr)
            except KeyError:
                wrong_attrs.append(attr)
        if wrong_attrs:
            raise InvalidParameterException(
                "Invalid user attributes: "
                + "\n".join(
                    [
                        f"user.{w}: Attribute does not exist in the schema."
                        for w in wrong_attrs
                    ]
                )
                + "\n"
            )
        self.attribute_lookup = flat_attributes
        self.attributes = expand_attrs(flat_attributes)


class CognitoResourceServer(BaseModel):
    def __init__(self, user_pool_id, identifier, name, scopes):
        self.user_pool_id = user_pool_id
        self.identifier = identifier
        self.name = name
        self.scopes = scopes

    def to_json(self):
        res = {
            "UserPoolId": self.user_pool_id,
            "Identifier": self.identifier,
            "Name": self.name,
        }

        if len(self.scopes) != 0:
            res.update({"Scopes": self.scopes})

        return res


class CognitoIdpBackend(BaseBackend):
    def __init__(self, region):
        super().__init__()
        self.region = region
        self.user_pools = OrderedDict()
        self.user_pool_domains = OrderedDict()
        self.sessions = {}

    def reset(self):
        region = self.region
        self.__dict__ = {}
        self.__init__(region)

    # User pool
    def create_user_pool(self, name, extended_config):
        user_pool = CognitoIdpUserPool(self.region, name, extended_config)
        self.user_pools[user_pool.id] = user_pool
        return user_pool

    def set_user_pool_mfa_config(
        self, user_pool_id, sms_config, token_config, mfa_config
    ):
        user_pool = self.describe_user_pool(user_pool_id)
        user_pool.mfa_config = mfa_config
        user_pool.sms_mfa_config = sms_config
        user_pool.token_mfa_config = token_config

        return self.get_user_pool_mfa_config(user_pool_id)

    def get_user_pool_mfa_config(self, user_pool_id):
        user_pool = self.describe_user_pool(user_pool_id)

        return {
            "SmsMfaConfiguration": user_pool.sms_mfa_config,
            "SoftwareTokenMfaConfiguration": user_pool.token_mfa_config,
            "MfaConfiguration": user_pool.mfa_config,
        }

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_user_pools(self):
        return list(self.user_pools.values())

    def describe_user_pool(self, user_pool_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(f"User pool {user_pool_id} does not exist.")

        return user_pool

    def update_user_pool(self, user_pool_id, extended_config):
        user_pool = self.describe_user_pool(user_pool_id)
        user_pool.extended_config = extended_config

    def delete_user_pool(self, user_pool_id):
        self.describe_user_pool(user_pool_id)

        del self.user_pools[user_pool_id]

    # User pool domain
    def create_user_pool_domain(self, user_pool_id, domain, custom_domain_config=None):
        self.describe_user_pool(user_pool_id)

        user_pool_domain = CognitoIdpUserPoolDomain(
            user_pool_id, domain, custom_domain_config=custom_domain_config
        )
        self.user_pool_domains[domain] = user_pool_domain
        return user_pool_domain

    def describe_user_pool_domain(self, domain):
        if domain not in self.user_pool_domains:
            return None

        return self.user_pool_domains[domain]

    def delete_user_pool_domain(self, domain):
        if domain not in self.user_pool_domains:
            raise ResourceNotFoundError(domain)

        del self.user_pool_domains[domain]

    def update_user_pool_domain(self, domain, custom_domain_config):
        if domain not in self.user_pool_domains:
            raise ResourceNotFoundError(domain)

        user_pool_domain = self.user_pool_domains[domain]
        user_pool_domain.custom_domain_config = custom_domain_config
        return user_pool_domain

    # User pool client
    def create_user_pool_client(self, user_pool_id, generate_secret, extended_config):
        user_pool = self.describe_user_pool(user_pool_id)

        user_pool_client = CognitoIdpUserPoolClient(
            user_pool_id, generate_secret, extended_config
        )
        user_pool.clients[user_pool_client.id] = user_pool_client
        return user_pool_client

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_user_pool_clients(self, user_pool_id):
        user_pool = self.describe_user_pool(user_pool_id)

        return list(user_pool.clients.values())

    def describe_user_pool_client(self, user_pool_id, client_id):
        user_pool = self.describe_user_pool(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        return client

    def update_user_pool_client(self, user_pool_id, client_id, extended_config):
        user_pool = self.describe_user_pool(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        client.extended_config.update(extended_config)
        return client

    def delete_user_pool_client(self, user_pool_id, client_id):
        user_pool = self.describe_user_pool(user_pool_id)

        if client_id not in user_pool.clients:
            raise ResourceNotFoundError(client_id)

        del user_pool.clients[client_id]

    # Identity provider
    def create_identity_provider(self, user_pool_id, name, extended_config):
        user_pool = self.describe_user_pool(user_pool_id)

        identity_provider = CognitoIdpIdentityProvider(name, extended_config)
        user_pool.identity_providers[name] = identity_provider
        return identity_provider

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_identity_providers(self, user_pool_id):
        user_pool = self.describe_user_pool(user_pool_id)

        return list(user_pool.identity_providers.values())

    def describe_identity_provider(self, user_pool_id, name):
        user_pool = self.describe_user_pool(user_pool_id)

        identity_provider = user_pool.identity_providers.get(name)
        if not identity_provider:
            raise ResourceNotFoundError(name)

        return identity_provider

    def update_identity_provider(self, user_pool_id, name, extended_config):
        user_pool = self.describe_user_pool(user_pool_id)

        identity_provider = user_pool.identity_providers.get(name)
        if not identity_provider:
            raise ResourceNotFoundError(name)

        identity_provider.extended_config.update(extended_config)

        return identity_provider

    def delete_identity_provider(self, user_pool_id, name):
        user_pool = self.describe_user_pool(user_pool_id)

        if name not in user_pool.identity_providers:
            raise ResourceNotFoundError(name)

        del user_pool.identity_providers[name]

    # Group
    def create_group(self, user_pool_id, group_name, description, role_arn, precedence):
        user_pool = self.describe_user_pool(user_pool_id)

        group = CognitoIdpGroup(
            user_pool_id, group_name, description, role_arn, precedence
        )
        if group.group_name in user_pool.groups:
            raise GroupExistsException("A group with the name already exists")
        user_pool.groups[group.group_name] = group

        return group

    def get_group(self, user_pool_id, group_name):
        user_pool = self.describe_user_pool(user_pool_id)

        if group_name not in user_pool.groups:
            raise ResourceNotFoundError(group_name)

        return user_pool.groups[group_name]

    def list_groups(self, user_pool_id):
        user_pool = self.describe_user_pool(user_pool_id)

        return user_pool.groups.values()

    def delete_group(self, user_pool_id, group_name):
        user_pool = self.describe_user_pool(user_pool_id)

        if group_name not in user_pool.groups:
            raise ResourceNotFoundError(group_name)

        group = user_pool.groups[group_name]
        for user in group.users:
            user.groups.remove(group)

        del user_pool.groups[group_name]

    def admin_add_user_to_group(self, user_pool_id, group_name, username):
        group = self.get_group(user_pool_id, group_name)
        user = self.admin_get_user(user_pool_id, username)

        group.users.add(user)
        user.groups.add(group)

    def list_users_in_group(self, user_pool_id, group_name):
        group = self.get_group(user_pool_id, group_name)
        return list(group.users)

    def admin_list_groups_for_user(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        return list(user.groups)

    def admin_remove_user_from_group(self, user_pool_id, group_name, username):
        group = self.get_group(user_pool_id, group_name)
        user = self.admin_get_user(user_pool_id, username)

        group.users.discard(user)
        user.groups.discard(group)

    def admin_reset_user_password(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        if not user.enabled:
            raise NotAuthorizedError("User is disabled")
        if user.status is UserStatus.RESET_REQUIRED:
            return
        if user.status is not UserStatus.CONFIRMED:
            raise NotAuthorizedError(
                "User password cannot be reset in the current state."
            )
        if (
            user.attribute_lookup.get("email_verified", "false") == "false"
            and user.attribute_lookup.get("phone_number_verified", "false") == "false"
        ):
            raise InvalidParameterException(
                "Cannot reset password for the user as there is no registered/verified email or phone_number"
            )
        user.status = UserStatus.RESET_REQUIRED

    # User
    def admin_create_user(
        self, user_pool_id, username, message_action, temporary_password, attributes
    ):
        user_pool = self.describe_user_pool(user_pool_id)

        if message_action and message_action == "RESEND":
            self.admin_get_user(user_pool_id, username)
        elif user_pool._get_user(username):
            raise UsernameExistsException(username)

        # UsernameAttributes are attributes (either `email` or `phone_number`
        # or both) than can be used in the place of a unique username. If the
        # user provides an email or phone number when signing up, the user pool
        # performs the following steps:
        # 1. populates the correct field (email, phone_number) with the value
        #    supplied for Username
        # 2. generates a persistent GUID for the user that will be returned as
        #    the value of `Username` in the `get-user` and `list-users`
        #    operations, as well as the value of `sub` in `IdToken` and
        #    `AccessToken`
        #
        # ref: https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html#user-pool-settings-aliases-settings
        if user_pool.extended_config.get("UsernameAttributes"):
            username_attributes = user_pool.extended_config["UsernameAttributes"]
            # attribute_type should be one of `email`, `phone_number` or both
            for attribute_type in username_attributes:
                # check if provided username matches one of the attribute types in
                # `UsernameAttributes`
                if attribute_type in username_attributes and validate_username_format(
                    username, _format=attribute_type
                ):
                    # insert provided username into new user's attributes under the
                    # correct key
                    flattened_attrs = flatten_attrs(attributes or {})
                    flattened_attrs.update({attribute_type: username})
                    attributes = expand_attrs(flattened_attrs)
                    # set username to None so that it will be default to the internal GUID
                    # when them user gets created
                    username = None
                    # once the username has been validated against a username attribute
                    # type, there is no need to attempt validation against the other
                    # type(s)
                    break

            # The provided username has not matched the required format for any
            # of the possible attributes
            if username is not None:
                raise InvalidParameterException(
                    "Username should be either an email or a phone number."
                )

        user = CognitoIdpUser(
            user_pool_id,
            username,
            temporary_password,
            UserStatus.FORCE_CHANGE_PASSWORD,
            attributes,
        )

        user_pool.users[user.username] = user
        return user

    def admin_confirm_sign_up(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        user.status = UserStatus["CONFIRMED"]
        return ""

    def admin_get_user(self, user_pool_id, username):
        user_pool = self.describe_user_pool(user_pool_id)

        user = user_pool._get_user(username)
        if not user:
            raise UserNotFoundError("User does not exist.")
        return user

    def get_user(self, access_token):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = self.admin_get_user(user_pool.id, username)
                if (
                    not user
                    or not user.enabled
                    or user.status is not UserStatus.CONFIRMED
                ):
                    raise NotAuthorizedError("username")
                return user
        raise NotAuthorizedError("Invalid token")

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_users(self, user_pool_id):
        user_pool = self.describe_user_pool(user_pool_id)

        return list(user_pool.users.values())

    def admin_disable_user(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        user.enabled = False

    def admin_enable_user(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        user.enabled = True

    def admin_delete_user(self, user_pool_id, username):
        user_pool = self.describe_user_pool(user_pool_id)
        user = self.admin_get_user(user_pool_id, username)

        for group in user.groups:
            group.users.remove(user)

        # use internal username
        del user_pool.users[user.username]

    def _log_user_in(self, user_pool, client, username):
        refresh_token = user_pool.create_refresh_token(client.id, username)
        access_token, id_token, expires_in = user_pool.create_tokens_from_refresh_token(
            refresh_token
        )

        return {
            "AuthenticationResult": {
                "IdToken": id_token,
                "AccessToken": access_token,
                "RefreshToken": refresh_token,
                "ExpiresIn": expires_in,
            }
        }

    def admin_initiate_auth(self, user_pool_id, client_id, auth_flow, auth_parameters):
        user_pool = self.describe_user_pool(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        if auth_flow in ("ADMIN_USER_PASSWORD_AUTH", "ADMIN_NO_SRP_AUTH"):
            username = auth_parameters.get("USERNAME")
            password = auth_parameters.get("PASSWORD")
            user = self.admin_get_user(user_pool_id, username)

            if user.password != password:
                raise NotAuthorizedError(username)

            if user.status in [
                UserStatus.FORCE_CHANGE_PASSWORD,
                UserStatus.RESET_REQUIRED,
            ]:
                session = str(uuid.uuid4())
                self.sessions[session] = user_pool

                return {
                    "ChallengeName": "NEW_PASSWORD_REQUIRED",
                    "ChallengeParameters": {},
                    "Session": session,
                }

            return self._log_user_in(user_pool, client, username)
        elif auth_flow == "REFRESH_TOKEN":
            refresh_token = auth_parameters.get("REFRESH_TOKEN")
            (
                id_token,
                access_token,
                expires_in,
            ) = user_pool.create_tokens_from_refresh_token(refresh_token)

            return {
                "AuthenticationResult": {
                    "IdToken": id_token,
                    "AccessToken": access_token,
                    "ExpiresIn": expires_in,
                }
            }
        else:
            return {}

    def respond_to_auth_challenge(
        self, session, client_id, challenge_name, challenge_responses
    ):
        if challenge_name == "PASSWORD_VERIFIER":
            session = challenge_responses.get("PASSWORD_CLAIM_SECRET_BLOCK")

        user_pool = self.sessions.get(session)
        if not user_pool:
            raise ResourceNotFoundError(session)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        if challenge_name == "NEW_PASSWORD_REQUIRED":
            username = challenge_responses.get("USERNAME")
            new_password = challenge_responses.get("NEW_PASSWORD")
            user = self.admin_get_user(user_pool.id, username)

            user.password = new_password
            user.status = UserStatus.CONFIRMED
            del self.sessions[session]

            return self._log_user_in(user_pool, client, username)
        elif challenge_name == "PASSWORD_VERIFIER":
            username = challenge_responses.get("USERNAME")
            user = self.admin_get_user(user_pool.id, username)

            password_claim_signature = challenge_responses.get(
                "PASSWORD_CLAIM_SIGNATURE"
            )
            if not password_claim_signature:
                raise ResourceNotFoundError(password_claim_signature)
            password_claim_secret_block = challenge_responses.get(
                "PASSWORD_CLAIM_SECRET_BLOCK"
            )
            if not password_claim_secret_block:
                raise ResourceNotFoundError(password_claim_secret_block)
            timestamp = challenge_responses.get("TIMESTAMP")
            if not timestamp:
                raise ResourceNotFoundError(timestamp)

            if user.software_token_mfa_enabled:
                return {
                    "ChallengeName": "SOFTWARE_TOKEN_MFA",
                    "Session": session,
                    "ChallengeParameters": {},
                }

            if user.sms_mfa_enabled:
                return {
                    "ChallengeName": "SMS_MFA",
                    "Session": session,
                    "ChallengeParameters": {},
                }

            del self.sessions[session]
            return self._log_user_in(user_pool, client, username)
        elif challenge_name == "SOFTWARE_TOKEN_MFA":
            username = challenge_responses.get("USERNAME")
            self.admin_get_user(user_pool.id, username)

            software_token_mfa_code = challenge_responses.get("SOFTWARE_TOKEN_MFA_CODE")
            if not software_token_mfa_code:
                raise ResourceNotFoundError(software_token_mfa_code)

            if client.generate_secret:
                secret_hash = challenge_responses.get("SECRET_HASH")
                if not check_secret_hash(
                    client.secret, client.id, username, secret_hash
                ):
                    raise NotAuthorizedError(secret_hash)

            del self.sessions[session]
            return self._log_user_in(user_pool, client, username)

        else:
            return {}

    def confirm_forgot_password(self, client_id, username, password, confirmation_code):
        for user_pool in self.user_pools.values():
            if client_id in user_pool.clients and user_pool._get_user(username):
                user = user_pool._get_user(username)
                if (
                    confirmation_code.startswith("moto-confirmation-code:")
                    and user.confirmation_code != confirmation_code
                ):
                    raise ExpiredCodeException(
                        "Invalid code provided, please request a code again."
                    )
                user.password = password
                user.confirmation_code = None
                break
        else:
            raise ResourceNotFoundError(client_id)

    def forgot_password(self, client_id, username):
        """The ForgotPassword operation is partially broken in AWS. If the input is 100% correct it works fine.
            Otherwise you get semi-random garbage and HTTP 200 OK, for example:
            - recovery for username which is not registered in any cognito pool
            - recovery for username belonging to a different user pool than the client id is registered to
            - phone-based recovery for a user without phone_number / phone_number_verified attributes
            - same as above, but email / email_verified
        """
        for user_pool in self.user_pools.values():
            if client_id in user_pool.clients:
                recovery_settings = user_pool._account_recovery_setting()
                user = user_pool._get_user(username)
                break
        else:
            raise ResourceNotFoundError("Username/client id combination not found.")

        confirmation_code = None
        if user:
            # An unfortunate bit of magic - confirmation_code is opt-in, as it's returned
            # via a "x-moto-forgot-password-confirmation-code" http header, which is not the AWS way (should be SES, SNS, Cognito built-in email)
            # Verification of user.confirmation_code vs received code will be performed only for codes
            # beginning with 'moto-confirmation-code' prefix. All other codes are considered VALID.
            confirmation_code = (
                f"moto-confirmation-code:{random.randint(100_000, 999_999)}"
            )
            user.confirmation_code = confirmation_code

        code_delivery_details = {
            "Destination": username + "@h***.com"
            if not user
            else user.attribute_lookup.get("email", username + "@h***.com"),
            "DeliveryMedium": "EMAIL",
            "AttributeName": "email",
        }
        selected_recovery = min(
            recovery_settings["RecoveryMechanisms"],
            key=lambda recovery_mechanism: recovery_mechanism["Priority"],
        )
        if selected_recovery["Name"] == "admin_only":
            raise NotAuthorizedError("Contact administrator to reset password.")
        if selected_recovery["Name"] == "verified_phone_number":
            code_delivery_details = {
                "Destination": "+*******9934"
                if not user
                else user.attribute_lookup.get("phone_number", "+*******9934"),
                "DeliveryMedium": "SMS",
                "AttributeName": "phone_number",
            }
        return confirmation_code, {"CodeDeliveryDetails": code_delivery_details}

    def change_password(self, access_token, previous_password, proposed_password):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = self.admin_get_user(user_pool.id, username)

                if user.password != previous_password:
                    raise NotAuthorizedError(username)

                user.password = proposed_password
                if user.status in [
                    UserStatus.FORCE_CHANGE_PASSWORD,
                    UserStatus.RESET_REQUIRED,
                ]:
                    user.status = UserStatus.CONFIRMED

                break
        else:
            raise NotAuthorizedError(access_token)

    def admin_update_user_attributes(self, user_pool_id, username, attributes):
        user = self.admin_get_user(user_pool_id, username)

        user.update_attributes(attributes)

    def admin_delete_user_attributes(self, user_pool_id, username, attributes):
        self.admin_get_user(user_pool_id, username).delete_attributes(attributes)

    def admin_user_global_sign_out(self, user_pool_id, username):
        user_pool = self.describe_user_pool(user_pool_id)
        self.admin_get_user(user_pool_id, username)

        for token, token_tuple in list(user_pool.refresh_tokens.items()):
            _, username = token_tuple
            if username == username:
                user_pool.refresh_tokens[token] = None

    def create_resource_server(self, user_pool_id, identifier, name, scopes):
        user_pool = self.describe_user_pool(user_pool_id)

        if identifier in user_pool.resource_servers:
            raise InvalidParameterException(
                "%s already exists in user pool %s." % (identifier, user_pool_id)
            )

        resource_server = CognitoResourceServer(user_pool_id, identifier, name, scopes)
        user_pool.resource_servers[identifier] = resource_server
        return resource_server

    def sign_up(self, client_id, username, password, attributes):
        user_pool = None
        for p in self.user_pools.values():
            if client_id in p.clients:
                user_pool = p
        if user_pool is None:
            raise ResourceNotFoundError(client_id)
        elif user_pool._get_user(username):
            raise UsernameExistsException(username)

        # UsernameAttributes are attributes (either `email` or `phone_number`
        # or both) than can be used in the place of a unique username. If the
        # user provides an email or phone number when signing up, the user pool
        # performs the following steps:
        # 1. populates the correct field (email, phone_number) with the value
        #    supplied for Username
        # 2. generates a persistent GUID for the user that will be returned as
        #    the value of `Username` in the `get-user` and `list-users`
        #    operations, as well as the value of `sub` in `IdToken` and
        #    `AccessToken`
        #
        # ref: https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html#user-pool-settings-aliases-settings
        if user_pool.extended_config.get("UsernameAttributes"):
            username_attributes = user_pool.extended_config["UsernameAttributes"]
            # attribute_type should be one of `email`, `phone_number` or both
            for attribute_type in username_attributes:
                # check if provided username matches one of the attribute types in
                # `UsernameAttributes`
                if attribute_type in username_attributes and validate_username_format(
                    username, _format=attribute_type
                ):
                    # insert provided username into new user's attributes under the
                    # correct key
                    flattened_attrs = flatten_attrs(attributes or {})
                    flattened_attrs.update({attribute_type: username})
                    attributes = expand_attrs(flattened_attrs)
                    # set username to None so that it will be default to the internal GUID
                    # when them user gets created
                    username = None
                    # once the username has been validated against a username attribute
                    # type, there is no need to attempt validation against the other
                    # type(s)
                    break

            # The provided username has not matched the required format for any
            # of the possible attributes
            if username is not None:
                raise InvalidParameterException(
                    "Username should be either an email or a phone number."
                )

        user = CognitoIdpUser(
            user_pool_id=user_pool.id,
            username=username,
            password=password,
            attributes=attributes,
            status=UserStatus.UNCONFIRMED,
        )
        user_pool.users[user.username] = user
        return user

    def confirm_sign_up(self, client_id, username, confirmation_code):
        user_pool = None
        for p in self.user_pools.values():
            if client_id in p.clients:
                user_pool = p
        if user_pool is None:
            raise ResourceNotFoundError(client_id)

        user = self.admin_get_user(user_pool.id, username)

        user.status = UserStatus.CONFIRMED
        return ""

    def initiate_auth(self, client_id, auth_flow, auth_parameters):
        user_pool = None
        for p in self.user_pools.values():
            if client_id in p.clients:
                user_pool = p
        if user_pool is None:
            raise ResourceNotFoundError(client_id)

        client = p.clients.get(client_id)

        if auth_flow == "USER_SRP_AUTH":
            username = auth_parameters.get("USERNAME")
            srp_a = auth_parameters.get("SRP_A")
            if not srp_a:
                raise ResourceNotFoundError(srp_a)
            if client.generate_secret:
                secret_hash = auth_parameters.get("SECRET_HASH")
                if not check_secret_hash(
                    client.secret, client.id, username, secret_hash
                ):
                    raise NotAuthorizedError(secret_hash)

            user = self.admin_get_user(user_pool.id, username)

            if user.status is UserStatus.UNCONFIRMED:
                raise UserNotConfirmedException("User is not confirmed.")

            session = str(uuid.uuid4())
            self.sessions[session] = user_pool

            return {
                "ChallengeName": "PASSWORD_VERIFIER",
                "Session": session,
                "ChallengeParameters": {
                    "SALT": uuid.uuid4().hex,
                    "SRP_B": uuid.uuid4().hex,
                    "USERNAME": user.id,
                    "USER_ID_FOR_SRP": user.id,
                    "SECRET_BLOCK": session,
                },
            }
        elif auth_flow == "USER_PASSWORD_AUTH":
            username = auth_parameters.get("USERNAME")
            password = auth_parameters.get("PASSWORD")

            user = self.admin_get_user(user_pool.id, username)

            if not user:
                raise UserNotFoundError(username)

            if user.password != password:
                raise NotAuthorizedError("Incorrect username or password.")

            if user.status is UserStatus.UNCONFIRMED:
                raise UserNotConfirmedException("User is not confirmed.")

            session = str(uuid.uuid4())
            self.sessions[session] = user_pool

            access_token, expires_in = user_pool.create_access_token(
                client_id, username
            )
            id_token, _ = user_pool.create_id_token(client_id, username)
            refresh_token = user_pool.create_refresh_token(client_id, username)

            return {
                "AuthenticationResult": {
                    "IdToken": id_token,
                    "AccessToken": access_token,
                    "ExpiresIn": expires_in,
                    "RefreshToken": refresh_token,
                    "TokenType": "Bearer",
                }
            }
        elif auth_flow == "REFRESH_TOKEN":
            refresh_token = auth_parameters.get("REFRESH_TOKEN")
            if not refresh_token:
                raise ResourceNotFoundError(refresh_token)

            if user_pool.refresh_tokens[refresh_token] is None:
                raise NotAuthorizedError("Refresh Token has been revoked")

            client_id, username = user_pool.refresh_tokens[refresh_token]
            if not username:
                raise ResourceNotFoundError(username)

            if client.generate_secret:
                secret_hash = auth_parameters.get("SECRET_HASH")
                if not check_secret_hash(
                    client.secret, client.id, username, secret_hash
                ):
                    raise NotAuthorizedError(secret_hash)

            (
                id_token,
                access_token,
                expires_in,
            ) = user_pool.create_tokens_from_refresh_token(refresh_token)

            return {
                "AuthenticationResult": {
                    "IdToken": id_token,
                    "AccessToken": access_token,
                    "ExpiresIn": expires_in,
                }
            }
        else:
            return None

    def associate_software_token(self, access_token):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                self.admin_get_user(user_pool.id, username)

                return {"SecretCode": str(uuid.uuid4())}
        else:
            raise NotAuthorizedError(access_token)

    def verify_software_token(self, access_token, user_code):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = self.admin_get_user(user_pool.id, username)

                user.token_verified = True

                return {"Status": "SUCCESS"}
        else:
            raise NotAuthorizedError(access_token)

    def set_user_mfa_preference(
        self, access_token, software_token_mfa_settings, sms_mfa_settings
    ):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = self.admin_get_user(user_pool.id, username)

                if software_token_mfa_settings["Enabled"]:
                    if user.token_verified:
                        user.software_token_mfa_enabled = True
                    else:
                        raise InvalidParameterException(
                            "User has not verified software token mfa"
                        )

                elif sms_mfa_settings["Enabled"]:
                    user.sms_mfa_enabled = True

                return None
        else:
            raise NotAuthorizedError(access_token)

    def admin_set_user_password(self, user_pool_id, username, password, permanent):
        user = self.admin_get_user(user_pool_id, username)
        user.password = password
        if permanent:
            user.status = UserStatus.CONFIRMED
        else:
            user.status = UserStatus.FORCE_CHANGE_PASSWORD

    def add_custom_attributes(self, user_pool_id, custom_attributes):
        user_pool = self.describe_user_pool(user_pool_id)
        user_pool.add_custom_attributes(custom_attributes)


cognitoidp_backends = {}
for region in Session().get_available_regions("cognito-idp"):
    cognitoidp_backends[region] = CognitoIdpBackend(region)
for region in Session().get_available_regions(
    "cognito-idp", partition_name="aws-us-gov"
):
    cognitoidp_backends[region] = CognitoIdpBackend(region)
for region in Session().get_available_regions("cognito-idp", partition_name="aws-cn"):
    cognitoidp_backends[region] = CognitoIdpBackend(region)


# Hack to help moto-server process requests on localhost, where the region isn't
# specified in the host header. Some endpoints (change password, confirm forgot
# password) have no authorization header from which to extract the region.
def find_region_by_value(key, value):
    for region in cognitoidp_backends:
        backend = cognitoidp_backends[region]
        for user_pool in backend.user_pools.values():
            if key == "client_id" and value in user_pool.clients:
                return region

            if key == "access_token" and value in user_pool.access_tokens:
                return region
    # If we can't find the `client_id` or `access_token`, we just pass
    # back a default backend region, which will raise the appropriate
    # error message (e.g. NotAuthorized or NotFound).
    return list(cognitoidp_backends)[0]
