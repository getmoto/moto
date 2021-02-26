from __future__ import unicode_literals

import datetime
import functools
import hashlib
import itertools
import json
import os
import time
import uuid

from boto3 import Session
from jose import jws

from moto.compat import OrderedDict
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
)
from .utils import create_id, check_secret_hash

UserStatus = {
    "FORCE_CHANGE_PASSWORD": "FORCE_CHANGE_PASSWORD",
    "CONFIRMED": "CONFIRMED",
    "UNCONFIRMED": "UNCONFIRMED",
}


def paginate(limit, start_arg="next_token", limit_arg="max_results"):
    """Returns a limited result list, and an offset into list of remaining items

    Takes the next_token, and max_results kwargs given to a function and handles
    the slicing of the results. The kwarg `next_token` is the offset into the
    list to begin slicing from. `max_results` is the size of the result required

    If the max_results is not supplied then the `limit` parameter is used as a
    default

    :param limit_arg: the name of argument in the decorated function that
    controls amount of items returned
    :param start_arg: the name of the argument in the decorated that provides
    the starting offset
    :param limit: A default maximum items to return
    :return: a tuple containing a list of items, and the offset into the list
    """
    default_start = 0

    def outer_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = int(
                default_start if kwargs.get(start_arg) is None else kwargs[start_arg]
            )
            lim = int(limit if kwargs.get(limit_arg) is None else kwargs[limit_arg])
            stop = start + lim
            result = func(*args, **kwargs)
            limited_results = list(itertools.islice(result, start, stop))
            next_token = stop if stop < len(result) else None
            return limited_results, next_token

        return wrapper

    return outer_wrapper


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

    def _base_json(self):
        return {
            "Id": self.id,
            "Arn": self.arn,
            "Name": self.name,
            "Status": self.status,
            "CreationDate": time.mktime(self.creation_date.timetuple()),
            "LastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
        }

    def to_json(self, extended=False):
        user_pool_json = self._base_json()
        if extended:
            user_pool_json.update(self.extended_config)
        else:
            user_pool_json["LambdaConfig"] = (
                self.extended_config.get("LambdaConfig") or {}
            )

        return user_pool_json

    def create_jwt(
        self, client_id, username, token_use, expires_in=60 * 60, extra_data={}
    ):
        now = int(time.time())
        payload = {
            "iss": "https://cognito-idp.{}.amazonaws.com/{}".format(
                self.region, self.id
            ),
            "sub": self.users[username].id,
            "aud": client_id,
            "token_use": token_use,
            "auth_time": now,
            "exp": now + expires_in,
        }
        payload.update(extra_data)
        headers = {"kid": "dummy"}  # KID as present in jwks-public.json

        return (
            jws.sign(payload, self.json_web_key, headers, algorithm="RS256"),
            expires_in,
        )

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
        access_token, expires_in = self.create_jwt(client_id, username, "access")
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
                        self.users.get(username).attributes,
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
            hash = hashlib.md5(
                self.custom_domain_config["CertificateArn"].encode("utf-8")
            ).hexdigest()
            return "{hash}.cloudfront.net".format(hash=hash[:16])
        hash = hashlib.md5(self.user_pool_id.encode("utf-8")).hexdigest()
        return "{hash}.amazoncognito.com".format(hash=hash[:16])

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
        self.username = username
        self.password = password
        self.status = status
        self.enabled = True
        self.attributes = attributes
        self.create_date = datetime.datetime.utcnow()
        self.last_modified_date = datetime.datetime.utcnow()
        self.sms_mfa_enabled = False
        self.software_token_mfa_enabled = False
        self.token_verified = False

        # Groups this user is a member of.
        # Note that these links are bidirectional.
        self.groups = set()

    def _base_json(self):
        return {
            "UserPoolId": self.user_pool_id,
            "Username": self.username,
            "UserStatus": self.status,
            "UserCreateDate": time.mktime(self.create_date.timetuple()),
            "UserLastModifiedDate": time.mktime(self.last_modified_date.timetuple()),
        }

    # list_users brings back "Attributes" while admin_get_user brings back "UserAttributes".
    def to_json(self, extended=False, attributes_key="Attributes"):
        user_mfa_setting_list = []
        if self.software_token_mfa_enabled:
            user_mfa_setting_list.append("SOFTWARE_TOKEN_MFA")
        elif self.sms_mfa_enabled:
            user_mfa_setting_list.append("SMS_MFA")
        user_json = self._base_json()
        if extended:
            user_json.update(
                {
                    "Enabled": self.enabled,
                    attributes_key: self.attributes,
                    "MFAOptions": [],
                    "UserMFASettingList": user_mfa_setting_list,
                }
            )

        return user_json

    def update_attributes(self, new_attributes):
        def flatten_attrs(attrs):
            return {attr["Name"]: attr["Value"] for attr in attrs}

        def expand_attrs(attrs):
            return [{"Name": k, "Value": v} for k, v in attrs.items()]

        flat_attributes = flatten_attrs(self.attributes)
        flat_attributes.update(flatten_attrs(new_attributes))
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
        super(CognitoIdpBackend, self).__init__()
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

    @paginate(60)
    def list_user_pools(self, max_results=None, next_token=None):
        return self.user_pools.values()

    def describe_user_pool(self, user_pool_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool

    def delete_user_pool(self, user_pool_id):
        if user_pool_id not in self.user_pools:
            raise ResourceNotFoundError(user_pool_id)

        del self.user_pools[user_pool_id]

    # User pool domain
    def create_user_pool_domain(self, user_pool_id, domain, custom_domain_config=None):
        if user_pool_id not in self.user_pools:
            raise ResourceNotFoundError(user_pool_id)

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
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        user_pool_client = CognitoIdpUserPoolClient(
            user_pool_id, generate_secret, extended_config
        )
        user_pool.clients[user_pool_client.id] = user_pool_client
        return user_pool_client

    @paginate(60)
    def list_user_pool_clients(self, user_pool_id, max_results=None, next_token=None):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool.clients.values()

    def describe_user_pool_client(self, user_pool_id, client_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        return client

    def update_user_pool_client(self, user_pool_id, client_id, extended_config):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        client.extended_config.update(extended_config)
        return client

    def delete_user_pool_client(self, user_pool_id, client_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if client_id not in user_pool.clients:
            raise ResourceNotFoundError(client_id)

        del user_pool.clients[client_id]

    # Identity provider
    def create_identity_provider(self, user_pool_id, name, extended_config):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        identity_provider = CognitoIdpIdentityProvider(name, extended_config)
        user_pool.identity_providers[name] = identity_provider
        return identity_provider

    @paginate(60)
    def list_identity_providers(self, user_pool_id, max_results=None, next_token=None):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool.identity_providers.values()

    def describe_identity_provider(self, user_pool_id, name):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        identity_provider = user_pool.identity_providers.get(name)
        if not identity_provider:
            raise ResourceNotFoundError(name)

        return identity_provider

    def update_identity_provider(self, user_pool_id, name, extended_config):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        identity_provider = user_pool.identity_providers.get(name)
        if not identity_provider:
            raise ResourceNotFoundError(name)

        identity_provider.extended_config.update(extended_config)

        return identity_provider

    def delete_identity_provider(self, user_pool_id, name):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if name not in user_pool.identity_providers:
            raise ResourceNotFoundError(name)

        del user_pool.identity_providers[name]

    # Group
    def create_group(self, user_pool_id, group_name, description, role_arn, precedence):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        group = CognitoIdpGroup(
            user_pool_id, group_name, description, role_arn, precedence
        )
        if group.group_name in user_pool.groups:
            raise GroupExistsException("A group with the name already exists")
        user_pool.groups[group.group_name] = group

        return group

    def get_group(self, user_pool_id, group_name):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if group_name not in user_pool.groups:
            raise ResourceNotFoundError(group_name)

        return user_pool.groups[group_name]

    def list_groups(self, user_pool_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool.groups.values()

    def delete_group(self, user_pool_id, group_name):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

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

    # User
    def admin_create_user(
        self, user_pool_id, username, message_action, temporary_password, attributes
    ):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if message_action and message_action == "RESEND":
            if username not in user_pool.users:
                raise UserNotFoundError(username)
        elif username in user_pool.users:
            raise UsernameExistsException(username)

        user = CognitoIdpUser(
            user_pool_id,
            username,
            temporary_password,
            UserStatus["FORCE_CHANGE_PASSWORD"],
            attributes,
        )
        user_pool.users[user.username] = user
        return user

    def admin_get_user(self, user_pool_id, username):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if username not in user_pool.users:
            raise UserNotFoundError(username)

        return user_pool.users[username]

    @paginate(60, "pagination_token", "limit")
    def list_users(self, user_pool_id, pagination_token=None, limit=None):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool.users.values()

    def admin_disable_user(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        user.enabled = False

    def admin_enable_user(self, user_pool_id, username):
        user = self.admin_get_user(user_pool_id, username)
        user.enabled = True

    def admin_delete_user(self, user_pool_id, username):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if username not in user_pool.users:
            raise UserNotFoundError(username)

        user = user_pool.users[username]
        for group in user.groups:
            group.users.remove(user)

        del user_pool.users[username]

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
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        client = user_pool.clients.get(client_id)
        if not client:
            raise ResourceNotFoundError(client_id)

        if auth_flow in ("ADMIN_USER_PASSWORD_AUTH", "ADMIN_NO_SRP_AUTH"):
            username = auth_parameters.get("USERNAME")
            password = auth_parameters.get("PASSWORD")
            user = user_pool.users.get(username)
            if not user:
                raise UserNotFoundError(username)

            if user.password != password:
                raise NotAuthorizedError(username)

            if user.status == UserStatus["FORCE_CHANGE_PASSWORD"]:
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
            user = user_pool.users.get(username)
            if not user:
                raise UserNotFoundError(username)

            user.password = new_password
            user.status = UserStatus["CONFIRMED"]
            del self.sessions[session]

            return self._log_user_in(user_pool, client, username)
        elif challenge_name == "PASSWORD_VERIFIER":
            username = challenge_responses.get("USERNAME")
            user = user_pool.users.get(username)
            if not user:
                raise UserNotFoundError(username)

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
            user = user_pool.users.get(username)
            if not user:
                raise UserNotFoundError(username)

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

    def confirm_forgot_password(self, client_id, username, password):
        for user_pool in self.user_pools.values():
            if client_id in user_pool.clients and username in user_pool.users:
                user_pool.users[username].password = password
                break
        else:
            raise ResourceNotFoundError(client_id)

    def change_password(self, access_token, previous_password, proposed_password):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = user_pool.users.get(username)
                if not user:
                    raise UserNotFoundError(username)

                if user.password != previous_password:
                    raise NotAuthorizedError(username)

                user.password = proposed_password
                if user.status == UserStatus["FORCE_CHANGE_PASSWORD"]:
                    user.status = UserStatus["CONFIRMED"]

                break
        else:
            raise NotAuthorizedError(access_token)

    def admin_update_user_attributes(self, user_pool_id, username, attributes):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if username not in user_pool.users:
            raise UserNotFoundError(username)

        user = user_pool.users[username]
        user.update_attributes(attributes)

    def create_resource_server(self, user_pool_id, identifier, name, scopes):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

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

        user = CognitoIdpUser(
            user_pool_id=user_pool.id,
            username=username,
            password=password,
            attributes=attributes,
            status=UserStatus["UNCONFIRMED"],
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

        if username not in user_pool.users:
            raise UserNotFoundError(username)

        user = user_pool.users[username]
        user.status = UserStatus["CONFIRMED"]
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

            user = user_pool.users.get(username)
            if not user:
                raise UserNotFoundError(username)

            if user.status == UserStatus["UNCONFIRMED"]:
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
        elif auth_flow == "REFRESH_TOKEN":
            refresh_token = auth_parameters.get("REFRESH_TOKEN")
            if not refresh_token:
                raise ResourceNotFoundError(refresh_token)

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
                user = user_pool.users.get(username)
                if not user:
                    raise UserNotFoundError(username)

                return {"SecretCode": str(uuid.uuid4())}
        else:
            raise NotAuthorizedError(access_token)

    def verify_software_token(self, access_token, user_code):
        for user_pool in self.user_pools.values():
            if access_token in user_pool.access_tokens:
                _, username = user_pool.access_tokens[access_token]
                user = user_pool.users.get(username)
                if not user:
                    raise UserNotFoundError(username)

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
                user = user_pool.users.get(username)
                if not user:
                    raise UserNotFoundError(username)

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
            user.status = UserStatus["CONFIRMED"]
        else:
            user.status = UserStatus["FORCE_CHANGE_PASSWORD"]


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
