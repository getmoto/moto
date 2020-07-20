from __future__ import unicode_literals

import json
import os

from moto.core.responses import BaseResponse
from .models import cognitoidp_backends, find_region_by_value


class CognitoIdpResponse(BaseResponse):
    @property
    def parameters(self):
        return json.loads(self.body)

    # User pool
    def create_user_pool(self):
        name = self.parameters.pop("PoolName")
        user_pool = cognitoidp_backends[self.region].create_user_pool(
            name, self.parameters
        )
        return json.dumps({"UserPool": user_pool.to_json(extended=True)})

    def list_user_pools(self):
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken", "0")
        user_pools, next_token = cognitoidp_backends[self.region].list_user_pools(
            max_results=max_results, next_token=next_token
        )
        response = {"UserPools": [user_pool.to_json() for user_pool in user_pools]}
        if next_token:
            response["NextToken"] = str(next_token)
        return json.dumps(response)

    def describe_user_pool(self):
        user_pool_id = self._get_param("UserPoolId")
        user_pool = cognitoidp_backends[self.region].describe_user_pool(user_pool_id)
        return json.dumps({"UserPool": user_pool.to_json(extended=True)})

    def delete_user_pool(self):
        user_pool_id = self._get_param("UserPoolId")
        cognitoidp_backends[self.region].delete_user_pool(user_pool_id)
        return ""

    # User pool domain
    def create_user_pool_domain(self):
        domain = self._get_param("Domain")
        user_pool_id = self._get_param("UserPoolId")
        custom_domain_config = self._get_param("CustomDomainConfig")
        user_pool_domain = cognitoidp_backends[self.region].create_user_pool_domain(
            user_pool_id, domain, custom_domain_config
        )
        domain_description = user_pool_domain.to_json(extended=False)
        if domain_description:
            return json.dumps(domain_description)
        return ""

    def describe_user_pool_domain(self):
        domain = self._get_param("Domain")
        user_pool_domain = cognitoidp_backends[self.region].describe_user_pool_domain(
            domain
        )
        domain_description = {}
        if user_pool_domain:
            domain_description = user_pool_domain.to_json()

        return json.dumps({"DomainDescription": domain_description})

    def delete_user_pool_domain(self):
        domain = self._get_param("Domain")
        cognitoidp_backends[self.region].delete_user_pool_domain(domain)
        return ""

    def update_user_pool_domain(self):
        domain = self._get_param("Domain")
        custom_domain_config = self._get_param("CustomDomainConfig")
        user_pool_domain = cognitoidp_backends[self.region].update_user_pool_domain(
            domain, custom_domain_config
        )
        domain_description = user_pool_domain.to_json(extended=False)
        if domain_description:
            return json.dumps(domain_description)
        return ""

    # User pool client
    def create_user_pool_client(self):
        user_pool_id = self.parameters.pop("UserPoolId")
        generate_secret = self.parameters.pop("GenerateSecret", False)
        user_pool_client = cognitoidp_backends[self.region].create_user_pool_client(
            user_pool_id, generate_secret, self.parameters
        )
        return json.dumps({"UserPoolClient": user_pool_client.to_json(extended=True)})

    def list_user_pool_clients(self):
        user_pool_id = self._get_param("UserPoolId")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken", "0")
        user_pool_clients, next_token = cognitoidp_backends[
            self.region
        ].list_user_pool_clients(
            user_pool_id, max_results=max_results, next_token=next_token
        )
        response = {
            "UserPoolClients": [
                user_pool_client.to_json() for user_pool_client in user_pool_clients
            ]
        }
        if next_token:
            response["NextToken"] = str(next_token)
        return json.dumps(response)

    def describe_user_pool_client(self):
        user_pool_id = self._get_param("UserPoolId")
        client_id = self._get_param("ClientId")
        user_pool_client = cognitoidp_backends[self.region].describe_user_pool_client(
            user_pool_id, client_id
        )
        return json.dumps({"UserPoolClient": user_pool_client.to_json(extended=True)})

    def update_user_pool_client(self):
        user_pool_id = self.parameters.pop("UserPoolId")
        client_id = self.parameters.pop("ClientId")
        user_pool_client = cognitoidp_backends[self.region].update_user_pool_client(
            user_pool_id, client_id, self.parameters
        )
        return json.dumps({"UserPoolClient": user_pool_client.to_json(extended=True)})

    def delete_user_pool_client(self):
        user_pool_id = self._get_param("UserPoolId")
        client_id = self._get_param("ClientId")
        cognitoidp_backends[self.region].delete_user_pool_client(
            user_pool_id, client_id
        )
        return ""

    # Identity provider
    def create_identity_provider(self):
        user_pool_id = self._get_param("UserPoolId")
        name = self.parameters.pop("ProviderName")
        identity_provider = cognitoidp_backends[self.region].create_identity_provider(
            user_pool_id, name, self.parameters
        )
        return json.dumps(
            {"IdentityProvider": identity_provider.to_json(extended=True)}
        )

    def list_identity_providers(self):
        user_pool_id = self._get_param("UserPoolId")
        max_results = self._get_param("MaxResults")
        next_token = self._get_param("NextToken", "0")
        identity_providers, next_token = cognitoidp_backends[
            self.region
        ].list_identity_providers(
            user_pool_id, max_results=max_results, next_token=next_token
        )
        response = {
            "Providers": [
                identity_provider.to_json() for identity_provider in identity_providers
            ]
        }
        if next_token:
            response["NextToken"] = str(next_token)
        return json.dumps(response)

    def describe_identity_provider(self):
        user_pool_id = self._get_param("UserPoolId")
        name = self._get_param("ProviderName")
        identity_provider = cognitoidp_backends[self.region].describe_identity_provider(
            user_pool_id, name
        )
        return json.dumps(
            {"IdentityProvider": identity_provider.to_json(extended=True)}
        )

    def update_identity_provider(self):
        user_pool_id = self._get_param("UserPoolId")
        name = self._get_param("ProviderName")
        identity_provider = cognitoidp_backends[self.region].update_identity_provider(
            user_pool_id, name, self.parameters
        )
        return json.dumps(
            {"IdentityProvider": identity_provider.to_json(extended=True)}
        )

    def delete_identity_provider(self):
        user_pool_id = self._get_param("UserPoolId")
        name = self._get_param("ProviderName")
        cognitoidp_backends[self.region].delete_identity_provider(user_pool_id, name)
        return ""

    # Group
    def create_group(self):
        group_name = self._get_param("GroupName")
        user_pool_id = self._get_param("UserPoolId")
        description = self._get_param("Description")
        role_arn = self._get_param("RoleArn")
        precedence = self._get_param("Precedence")

        group = cognitoidp_backends[self.region].create_group(
            user_pool_id, group_name, description, role_arn, precedence
        )

        return json.dumps({"Group": group.to_json()})

    def get_group(self):
        group_name = self._get_param("GroupName")
        user_pool_id = self._get_param("UserPoolId")
        group = cognitoidp_backends[self.region].get_group(user_pool_id, group_name)
        return json.dumps({"Group": group.to_json()})

    def list_groups(self):
        user_pool_id = self._get_param("UserPoolId")
        groups = cognitoidp_backends[self.region].list_groups(user_pool_id)
        return json.dumps({"Groups": [group.to_json() for group in groups]})

    def delete_group(self):
        group_name = self._get_param("GroupName")
        user_pool_id = self._get_param("UserPoolId")
        cognitoidp_backends[self.region].delete_group(user_pool_id, group_name)
        return ""

    def admin_add_user_to_group(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        group_name = self._get_param("GroupName")

        cognitoidp_backends[self.region].admin_add_user_to_group(
            user_pool_id, group_name, username
        )

        return ""

    def list_users_in_group(self):
        user_pool_id = self._get_param("UserPoolId")
        group_name = self._get_param("GroupName")
        users = cognitoidp_backends[self.region].list_users_in_group(
            user_pool_id, group_name
        )
        return json.dumps({"Users": [user.to_json(extended=True) for user in users]})

    def admin_list_groups_for_user(self):
        username = self._get_param("Username")
        user_pool_id = self._get_param("UserPoolId")
        groups = cognitoidp_backends[self.region].admin_list_groups_for_user(
            user_pool_id, username
        )
        return json.dumps({"Groups": [group.to_json() for group in groups]})

    def admin_remove_user_from_group(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        group_name = self._get_param("GroupName")

        cognitoidp_backends[self.region].admin_remove_user_from_group(
            user_pool_id, group_name, username
        )

        return ""

    # User
    def admin_create_user(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        message_action = self._get_param("MessageAction")
        temporary_password = self._get_param("TemporaryPassword")
        user = cognitoidp_backends[self.region].admin_create_user(
            user_pool_id,
            username,
            message_action,
            temporary_password,
            self._get_param("UserAttributes", []),
        )

        return json.dumps({"User": user.to_json(extended=True)})

    def admin_get_user(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        user = cognitoidp_backends[self.region].admin_get_user(user_pool_id, username)
        return json.dumps(user.to_json(extended=True, attributes_key="UserAttributes"))

    def list_users(self):
        user_pool_id = self._get_param("UserPoolId")
        limit = self._get_param("Limit")
        token = self._get_param("PaginationToken")
        filt = self._get_param("Filter")
        users, token = cognitoidp_backends[self.region].list_users(
            user_pool_id, limit=limit, pagination_token=token
        )
        if filt:
            name, value = filt.replace('"', "").split("=")
            users = [
                user
                for user in users
                for attribute in user.attributes
                if attribute["Name"] == name and attribute["Value"] == value
            ]
        response = {"Users": [user.to_json(extended=True) for user in users]}
        if token:
            response["PaginationToken"] = str(token)
        return json.dumps(response)

    def admin_disable_user(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        cognitoidp_backends[self.region].admin_disable_user(user_pool_id, username)
        return ""

    def admin_enable_user(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        cognitoidp_backends[self.region].admin_enable_user(user_pool_id, username)
        return ""

    def admin_delete_user(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        cognitoidp_backends[self.region].admin_delete_user(user_pool_id, username)
        return ""

    def admin_initiate_auth(self):
        user_pool_id = self._get_param("UserPoolId")
        client_id = self._get_param("ClientId")
        auth_flow = self._get_param("AuthFlow")
        auth_parameters = self._get_param("AuthParameters")

        auth_result = cognitoidp_backends[self.region].admin_initiate_auth(
            user_pool_id, client_id, auth_flow, auth_parameters
        )

        return json.dumps(auth_result)

    def respond_to_auth_challenge(self):
        session = self._get_param("Session")
        client_id = self._get_param("ClientId")
        challenge_name = self._get_param("ChallengeName")
        challenge_responses = self._get_param("ChallengeResponses")
        auth_result = cognitoidp_backends[self.region].respond_to_auth_challenge(
            session, client_id, challenge_name, challenge_responses
        )

        return json.dumps(auth_result)

    def forgot_password(self):
        return json.dumps(
            {"CodeDeliveryDetails": {"DeliveryMedium": "EMAIL", "Destination": "..."}}
        )

    # This endpoint receives no authorization header, so if moto-server is listening
    # on localhost (doesn't get a region in the host header), it doesn't know what
    # region's backend should handle the traffic, and we use `find_region_by_value` to
    # solve that problem.
    def confirm_forgot_password(self):
        client_id = self._get_param("ClientId")
        username = self._get_param("Username")
        password = self._get_param("Password")
        region = find_region_by_value("client_id", client_id)
        cognitoidp_backends[region].confirm_forgot_password(
            client_id, username, password
        )
        return ""

    # Ditto the comment on confirm_forgot_password.
    def change_password(self):
        access_token = self._get_param("AccessToken")
        previous_password = self._get_param("PreviousPassword")
        proposed_password = self._get_param("ProposedPassword")
        region = find_region_by_value("access_token", access_token)
        cognitoidp_backends[region].change_password(
            access_token, previous_password, proposed_password
        )
        return ""

    def admin_update_user_attributes(self):
        user_pool_id = self._get_param("UserPoolId")
        username = self._get_param("Username")
        attributes = self._get_param("UserAttributes")
        cognitoidp_backends[self.region].admin_update_user_attributes(
            user_pool_id, username, attributes
        )
        return ""

    # Resource Server
    def create_resource_server(self):
        user_pool_id = self._get_param("UserPoolId")
        identifier = self._get_param("Identifier")
        name = self._get_param("Name")
        scopes = self._get_param("Scopes")
        resource_server = cognitoidp_backends[self.region].create_resource_server(
            user_pool_id, identifier, name, scopes
        )
        return json.dumps({"ResourceServer": resource_server.to_json()})


class CognitoIdpJsonWebKeyResponse(BaseResponse):
    def __init__(self):
        with open(
            os.path.join(os.path.dirname(__file__), "resources/jwks-public.json")
        ) as f:
            self.json_web_key = f.read()

    def serve_json_web_key(self, request, full_url, headers):
        return 200, {"Content-Type": "application/json"}, self.json_web_key
