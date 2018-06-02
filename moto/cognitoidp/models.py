from __future__ import unicode_literals

import datetime
import json
import os
import time
import uuid

import boto.cognito.identity
from jose import jws

from moto.compat import OrderedDict
from moto.core import BaseBackend, BaseModel
from .exceptions import NotAuthorizedError, ResourceNotFoundError, UserNotFoundError


UserStatus = {
    "FORCE_CHANGE_PASSWORD": "FORCE_CHANGE_PASSWORD",
    "CONFIRMED": "CONFIRMED",
}


class CognitoIdpUserPool(BaseModel):

    def __init__(self, region, name, extended_config):
        self.region = region
        self.id = str(uuid.uuid4())
        self.name = name
        self.status = None
        self.extended_config = extended_config or {}
        self.creation_date = datetime.datetime.utcnow()
        self.last_modified_date = datetime.datetime.utcnow()

        self.clients = OrderedDict()
        self.identity_providers = OrderedDict()
        self.users = OrderedDict()
        self.refresh_tokens = {}
        self.access_tokens = {}
        self.id_tokens = {}

        with open(os.path.join(os.path.dirname(__file__), "resources/jwks-private.json")) as f:
            self.json_web_key = json.loads(f.read())

    def _base_json(self):
        return {
            "Id": self.id,
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
            user_pool_json["LambdaConfig"] = self.extended_config.get("LambdaConfig") or {}

        return user_pool_json

    def create_jwt(self, client_id, username, expires_in=60 * 60, extra_data={}):
        now = int(time.time())
        payload = {
            "iss": "https://cognito-idp.{}.amazonaws.com/{}".format(self.region, self.id),
            "sub": self.users[username].id,
            "aud": client_id,
            "token_use": "id",
            "auth_time": now,
            "exp": now + expires_in,
        }
        payload.update(extra_data)

        return jws.sign(payload, self.json_web_key, algorithm='RS256'), expires_in

    def create_id_token(self, client_id, username):
        id_token, expires_in = self.create_jwt(client_id, username)
        self.id_tokens[id_token] = (client_id, username)
        return id_token, expires_in

    def create_refresh_token(self, client_id, username):
        refresh_token = str(uuid.uuid4())
        self.refresh_tokens[refresh_token] = (client_id, username)
        return refresh_token

    def create_access_token(self, client_id, username):
        access_token, expires_in = self.create_jwt(client_id, username)
        self.access_tokens[access_token] = (client_id, username)
        return access_token, expires_in

    def create_tokens_from_refresh_token(self, refresh_token):
        client_id, username = self.refresh_tokens.get(refresh_token)
        if not username:
            raise NotAuthorizedError(refresh_token)

        access_token, expires_in = self.create_access_token(client_id, username)
        id_token, _ = self.create_id_token(client_id, username)
        return access_token, id_token, expires_in


class CognitoIdpUserPoolDomain(BaseModel):

    def __init__(self, user_pool_id, domain):
        self.user_pool_id = user_pool_id
        self.domain = domain

    def to_json(self):
        return {
            "UserPoolId": self.user_pool_id,
            "AWSAccountId": str(uuid.uuid4()),
            "CloudFrontDistribution": None,
            "Domain": self.domain,
            "S3Bucket": None,
            "Status": "ACTIVE",
            "Version": None,
        }


class CognitoIdpUserPoolClient(BaseModel):

    def __init__(self, user_pool_id, extended_config):
        self.user_pool_id = user_pool_id
        self.id = str(uuid.uuid4())
        self.secret = str(uuid.uuid4())
        self.extended_config = extended_config or {}

    def _base_json(self):
        return {
            "ClientId": self.id,
            "ClientName": self.extended_config.get("ClientName"),
            "UserPoolId": self.user_pool_id,
        }

    def to_json(self, extended=False):
        user_pool_client_json = self._base_json()
        if extended:
            user_pool_client_json.update(self.extended_config)

        return user_pool_client_json


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
        user_json = self._base_json()
        if extended:
            user_json.update(
                {
                    "Enabled": self.enabled,
                    attributes_key: self.attributes,
                    "MFAOptions": []
                }
            )

        return user_json


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

    def list_user_pools(self):
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
    def create_user_pool_domain(self, user_pool_id, domain):
        if user_pool_id not in self.user_pools:
            raise ResourceNotFoundError(user_pool_id)

        user_pool_domain = CognitoIdpUserPoolDomain(user_pool_id, domain)
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

    # User pool client
    def create_user_pool_client(self, user_pool_id, extended_config):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        user_pool_client = CognitoIdpUserPoolClient(user_pool_id, extended_config)
        user_pool.clients[user_pool_client.id] = user_pool_client
        return user_pool_client

    def list_user_pool_clients(self, user_pool_id):
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

    def list_identity_providers(self, user_pool_id):
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

    def delete_identity_provider(self, user_pool_id, name):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if name not in user_pool.identity_providers:
            raise ResourceNotFoundError(name)

        del user_pool.identity_providers[name]

    # User
    def admin_create_user(self, user_pool_id, username, temporary_password, attributes):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        user = CognitoIdpUser(user_pool_id, username, temporary_password, UserStatus["FORCE_CHANGE_PASSWORD"], attributes)
        user_pool.users[user.username] = user
        return user

    def admin_get_user(self, user_pool_id, username):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if username not in user_pool.users:
            raise ResourceNotFoundError(username)

        return user_pool.users[username]

    def list_users(self, user_pool_id):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        return user_pool.users.values()

    def admin_delete_user(self, user_pool_id, username):
        user_pool = self.user_pools.get(user_pool_id)
        if not user_pool:
            raise ResourceNotFoundError(user_pool_id)

        if username not in user_pool.users:
            raise ResourceNotFoundError(username)

        del user_pool.users[username]

    def _log_user_in(self, user_pool, client, username):
        refresh_token = user_pool.create_refresh_token(client.id, username)
        access_token, id_token, expires_in = user_pool.create_tokens_from_refresh_token(refresh_token)

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

        if auth_flow == "ADMIN_NO_SRP_AUTH":
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
            id_token, access_token, expires_in = user_pool.create_tokens_from_refresh_token(refresh_token)

            return {
                "AuthenticationResult": {
                    "IdToken": id_token,
                    "AccessToken": access_token,
                    "ExpiresIn": expires_in,
                }
            }
        else:
            return {}

    def respond_to_auth_challenge(self, session, client_id, challenge_name, challenge_responses):
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


cognitoidp_backends = {}
for region in boto.cognito.identity.regions():
    cognitoidp_backends[region.name] = CognitoIdpBackend(region.name)


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

    return cognitoidp_backends.keys()[0]
