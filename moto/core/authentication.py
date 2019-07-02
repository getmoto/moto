import json
import re
from enum import Enum

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from moto.iam.models import ACCOUNT_ID, Policy

from moto.iam import iam_backend

from moto.core.exceptions import SignatureDoesNotMatchError, AccessDeniedError, InvalidClientTokenIdError

ACCESS_KEY_STORE = {
    "AKIAJDULPKHCC4KGTYVA": {
        "owner": "avatao-user",
        "secret_access_key": "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"
    }
}


class IAMRequest:

    def __init__(self, method, path, data, headers):
        print(f"Creating {IAMRequest.__name__} with method={method}, path={path}, data={data}, headers={headers}")
        self._method = method
        self._path = path
        self._data = data
        self._headers = headers
        credential_scope = self._get_string_between('Credential=', ',', self._headers['Authorization'])
        credential_data = credential_scope.split('/')
        self._access_key = credential_data[0]
        self._region = credential_data[2]
        self._service = credential_data[3]
        self._action = self._service + ":" + self._data["Action"][0]

    def check_signature(self):
        original_signature = self._get_string_between('Signature=', ',', self._headers['Authorization'])
        calculated_signature = self._calculate_signature()
        if original_signature != calculated_signature:
            raise SignatureDoesNotMatchError()

    def check_action_permitted(self):
        iam_user_name = ACCESS_KEY_STORE[self._access_key]["owner"]
        user_policies = self._collect_policies_for_iam_user(iam_user_name)

        permitted = False
        for policy in user_policies:
            iam_policy = IAMPolicy(policy)
            permission_result = iam_policy.is_action_permitted(self._action)
            if permission_result == PermissionResult.DENIED:
                self._raise_access_denied(iam_user_name)
            elif permission_result == PermissionResult.PERMITTED:
                permitted = True

        if not permitted:
            self._raise_access_denied(iam_user_name)

    def _raise_access_denied(self, iam_user_name):
        raise AccessDeniedError(
            account_id=ACCOUNT_ID,
            iam_user_name=iam_user_name,
            action=self._action
        )

    @staticmethod
    def _collect_policies_for_iam_user(iam_user_name):
        user_policies = []

        inline_policy_names = iam_backend.list_user_policies(iam_user_name)
        for inline_policy_name in inline_policy_names:
            inline_policy = iam_backend.get_user_policy(iam_user_name, inline_policy_name)
            user_policies.append(inline_policy)

        attached_policies, _ = iam_backend.list_attached_user_policies(iam_user_name)
        user_policies += attached_policies

        user_groups = iam_backend.get_groups_for_user(iam_user_name)
        for user_group in user_groups:
            inline_group_policy_names = iam_backend.list_group_policies(user_group)
            for inline_group_policy_name in inline_group_policy_names:
                inline_user_group_policy = iam_backend.get_group_policy(user_group.name, inline_group_policy_name)
                user_policies.append(inline_user_group_policy)

            attached_group_policies = iam_backend.list_attached_group_policies(user_group.name)
            user_policies += attached_group_policies

        return user_policies

    def _create_auth(self):
        if self._access_key not in ACCESS_KEY_STORE:
            raise InvalidClientTokenIdError()
        secret_key = ACCESS_KEY_STORE[self._access_key]["secret_access_key"]

        credentials = Credentials(self._access_key, secret_key)
        return SigV4Auth(credentials, self._service, self._region)

    @staticmethod
    def _create_headers_for_aws_request(signed_headers, original_headers):
        headers = {}
        for key, value in original_headers.items():
            if key.lower() in signed_headers:
                headers[key] = value
        return headers

    def _create_aws_request(self):
        signed_headers = self._get_string_between('SignedHeaders=', ',', self._headers['Authorization']).split(';')
        headers = self._create_headers_for_aws_request(signed_headers, self._headers)
        request = AWSRequest(method=self._method, url=self._path, data=self._data, headers=headers)
        request.context['timestamp'] = headers['X-Amz-Date']

        return request

    def _calculate_signature(self):
        auth = self._create_auth()
        request = self._create_aws_request()
        canonical_request = auth.canonical_request(request)
        string_to_sign = auth.string_to_sign(request, canonical_request)
        return auth.signature(string_to_sign, request)

    @staticmethod
    def _get_string_between(first_separator, second_separator, string):
        return string.partition(first_separator)[2].partition(second_separator)[0]


class IAMPolicy:

    def __init__(self, policy):
        self._policy = policy

    def is_action_permitted(self, action):
        if isinstance(self._policy, Policy):
            default_version = next(policy_version for policy_version in self._policy.versions if policy_version.is_default)
            policy_document = default_version.document
        else:
            policy_document = self._policy["policy_document"]

        policy_json = json.loads(policy_document)

        permitted = False
        for policy_statement in policy_json["Statement"]:
            iam_policy_statement = IAMPolicyStatement(policy_statement)
            permission_result = iam_policy_statement.is_action_permitted(action)
            if permission_result == PermissionResult.DENIED:
                return permission_result
            elif permission_result == PermissionResult.PERMITTED:
                permitted = True

        if permitted:
            return PermissionResult.PERMITTED
        else:
            return PermissionResult.NEUTRAL


class IAMPolicyStatement:

    def __init__(self, statement):
        self._statement = statement

    def is_action_permitted(self, action):
        is_action_concerned = False

        if "NotAction" in self._statement:
            if not self._check_element_matches("NotAction", action):
                is_action_concerned = True
        else:  # Action is present
            if self._check_element_matches("Action", action):
                is_action_concerned = True

        # TODO: check Resource/NotResource and Condition

        if is_action_concerned:
            if self._statement["Effect"] == "Allow":
                return PermissionResult.PERMITTED
            else:  # Deny
                return PermissionResult.DENIED
        else:
            return PermissionResult.NEUTRAL

    def _check_element_matches(self, statement_element, value):
        if isinstance(self._statement[statement_element], list):
            for statement_element_value in self._statement[statement_element]:
                if self._match(statement_element_value, value):
                    return True
            return False
        else:  # string
            return self._match(self._statement[statement_element], value)

    @staticmethod
    def _match(pattern, string):
        pattern = pattern.replace("*", ".*")
        pattern = f"^{pattern}$"
        return re.match(pattern, string)


class PermissionResult(Enum):
    PERMITTED = 1
    DENIED = 2
    NEUTRAL = 3
