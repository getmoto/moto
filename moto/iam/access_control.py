"""
This implementation is NOT complete, there are many things to improve.
The following is a list of the most important missing features and inaccuracies.

TODO add support for more principals, apart from IAM users and assumed IAM roles
TODO add support for the Resource and Condition parts of IAM policies
TODO add support and create tests for all services in moto (for example, API Gateway is probably not supported currently)
TODO implement service specific error messages (currently, EC2 and S3 are supported separately, everything else defaults to the errors IAM returns)
TODO include information about the action's resource in error messages (once the Resource element in IAM policies is supported)
TODO check all other actions that are performed by the action called by the user (for example, autoscaling:CreateAutoScalingGroup requires permission for iam:CreateServiceLinkedRole too - see https://docs.aws.amazon.com/autoscaling/ec2/userguide/control-access-using-iam.html)
TODO add support for resource-based policies

"""

import json
import logging
import re
from abc import abstractmethod, ABCMeta
from enum import Enum

from botocore.auth import SigV4Auth, S3SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

from moto.core import ACCOUNT_ID
from moto.core.exceptions import (
    SignatureDoesNotMatchError,
    AccessDeniedError,
    InvalidClientTokenIdError,
    AuthFailureError,
)
from moto.s3.exceptions import (
    BucketAccessDeniedError,
    S3AccessDeniedError,
    BucketInvalidTokenError,
    S3InvalidTokenError,
    S3InvalidAccessKeyIdError,
    BucketInvalidAccessKeyIdError,
    BucketSignatureDoesNotMatchError,
    S3SignatureDoesNotMatchError,
)
from moto.sts import sts_backend
from .models import iam_backend, Policy

log = logging.getLogger(__name__)


def create_access_key(access_key_id, headers):
    if access_key_id.startswith("AKIA") or "X-Amz-Security-Token" not in headers:
        return IAMUserAccessKey(access_key_id, headers)
    else:
        return AssumedRoleAccessKey(access_key_id, headers)


class IAMUserAccessKey(object):
    def __init__(self, access_key_id, headers):
        iam_users = iam_backend.list_users("/", None, None)
        for iam_user in iam_users:
            for access_key in iam_user.access_keys:
                if access_key.access_key_id == access_key_id:
                    self._owner_user_name = iam_user.name
                    self._access_key_id = access_key_id
                    self._secret_access_key = access_key.secret_access_key
                    if "X-Amz-Security-Token" in headers:
                        raise CreateAccessKeyFailure(reason="InvalidToken")
                    return
        raise CreateAccessKeyFailure(reason="InvalidId")

    @property
    def arn(self):
        return "arn:aws:iam::{account_id}:user/{iam_user_name}".format(
            account_id=ACCOUNT_ID, iam_user_name=self._owner_user_name
        )

    def create_credentials(self):
        return Credentials(self._access_key_id, self._secret_access_key)

    def collect_policies(self):
        user_policies = []

        inline_policy_names = iam_backend.list_user_policies(self._owner_user_name)
        for inline_policy_name in inline_policy_names:
            inline_policy = iam_backend.get_user_policy(
                self._owner_user_name, inline_policy_name
            )
            user_policies.append(inline_policy)

        attached_policies, _ = iam_backend.list_attached_user_policies(
            self._owner_user_name
        )
        user_policies += attached_policies

        user_groups = iam_backend.get_groups_for_user(self._owner_user_name)
        for user_group in user_groups:
            inline_group_policy_names = iam_backend.list_group_policies(user_group.name)
            for inline_group_policy_name in inline_group_policy_names:
                inline_user_group_policy = iam_backend.get_group_policy(
                    user_group.name, inline_group_policy_name
                )
                user_policies.append(inline_user_group_policy)

            attached_group_policies, _ = iam_backend.list_attached_group_policies(
                user_group.name
            )
            user_policies += attached_group_policies

        return user_policies


class AssumedRoleAccessKey(object):
    def __init__(self, access_key_id, headers):
        for assumed_role in sts_backend.assumed_roles:
            if assumed_role.access_key_id == access_key_id:
                self._access_key_id = access_key_id
                self._secret_access_key = assumed_role.secret_access_key
                self._session_token = assumed_role.session_token
                self._owner_role_name = assumed_role.role_arn.split("/")[-1]
                self._session_name = assumed_role.session_name
                if headers["X-Amz-Security-Token"] != self._session_token:
                    raise CreateAccessKeyFailure(reason="InvalidToken")
                return
        raise CreateAccessKeyFailure(reason="InvalidId")

    @property
    def arn(self):
        return "arn:aws:sts::{account_id}:assumed-role/{role_name}/{session_name}".format(
            account_id=ACCOUNT_ID,
            role_name=self._owner_role_name,
            session_name=self._session_name,
        )

    def create_credentials(self):
        return Credentials(
            self._access_key_id, self._secret_access_key, self._session_token
        )

    def collect_policies(self):
        role_policies = []

        inline_policy_names = iam_backend.list_role_policies(self._owner_role_name)
        for inline_policy_name in inline_policy_names:
            _, inline_policy = iam_backend.get_role_policy(
                self._owner_role_name, inline_policy_name
            )
            role_policies.append(inline_policy)

        attached_policies, _ = iam_backend.list_attached_role_policies(
            self._owner_role_name
        )
        role_policies += attached_policies

        return role_policies


class CreateAccessKeyFailure(Exception):
    def __init__(self, reason, *args):
        super(CreateAccessKeyFailure, self).__init__(*args)
        self.reason = reason


class IAMRequestBase(object, metaclass=ABCMeta):
    def __init__(self, method, path, data, headers):
        log.debug(
            "Creating {class_name} with method={method}, path={path}, data={data}, headers={headers}".format(
                class_name=self.__class__.__name__,
                method=method,
                path=path,
                data=data,
                headers=headers,
            )
        )
        self._method = method
        self._path = path
        self._data = data
        self._headers = headers
        credential_scope = self._get_string_between(
            "Credential=", ",", self._headers["Authorization"]
        )
        credential_data = credential_scope.split("/")
        self._region = credential_data[2]
        self._service = credential_data[3]
        self._action = (
            self._service
            + ":"
            + (
                self._data["Action"][0]
                if isinstance(self._data["Action"], list)
                else self._data["Action"]
            )
        )
        try:
            self._access_key = create_access_key(
                access_key_id=credential_data[0], headers=headers
            )
        except CreateAccessKeyFailure as e:
            self._raise_invalid_access_key(e.reason)

    def check_signature(self):
        original_signature = self._get_string_between(
            "Signature=", ",", self._headers["Authorization"]
        )
        calculated_signature = self._calculate_signature()
        if original_signature != calculated_signature:
            self._raise_signature_does_not_match()

    def check_action_permitted(self):
        if (
            self._action == "sts:GetCallerIdentity"
        ):  # always allowed, even if there's an explicit Deny for it
            return True
        policies = self._access_key.collect_policies()

        permitted = False
        for policy in policies:
            iam_policy = IAMPolicy(policy)
            permission_result = iam_policy.is_action_permitted(self._action)
            if permission_result == PermissionResult.DENIED:
                self._raise_access_denied()
            elif permission_result == PermissionResult.PERMITTED:
                permitted = True

        if not permitted:
            self._raise_access_denied()

    @abstractmethod
    def _raise_signature_does_not_match(self):
        raise NotImplementedError()

    @abstractmethod
    def _raise_access_denied(self):
        raise NotImplementedError()

    @abstractmethod
    def _raise_invalid_access_key(self, reason):
        raise NotImplementedError()

    @abstractmethod
    def _create_auth(self, credentials):
        raise NotImplementedError()

    @staticmethod
    def _create_headers_for_aws_request(signed_headers, original_headers):
        headers = {}
        for key, value in original_headers.items():
            if key.lower() in signed_headers:
                headers[key] = value
        return headers

    def _create_aws_request(self):
        signed_headers = self._get_string_between(
            "SignedHeaders=", ",", self._headers["Authorization"]
        ).split(";")
        headers = self._create_headers_for_aws_request(signed_headers, self._headers)
        request = AWSRequest(
            method=self._method, url=self._path, data=self._data, headers=headers
        )
        request.context["timestamp"] = headers["X-Amz-Date"]

        return request

    def _calculate_signature(self):
        credentials = self._access_key.create_credentials()
        auth = self._create_auth(credentials)
        request = self._create_aws_request()
        canonical_request = auth.canonical_request(request)
        string_to_sign = auth.string_to_sign(request, canonical_request)
        return auth.signature(string_to_sign, request)

    @staticmethod
    def _get_string_between(first_separator, second_separator, string):
        return string.partition(first_separator)[2].partition(second_separator)[0]


class IAMRequest(IAMRequestBase):
    def _raise_signature_does_not_match(self):
        if self._service == "ec2":
            raise AuthFailureError()
        else:
            raise SignatureDoesNotMatchError()

    def _raise_invalid_access_key(self, _):
        if self._service == "ec2":
            raise AuthFailureError()
        else:
            raise InvalidClientTokenIdError()

    def _create_auth(self, credentials):
        return SigV4Auth(credentials, self._service, self._region)

    def _raise_access_denied(self):
        raise AccessDeniedError(user_arn=self._access_key.arn, action=self._action)


class S3IAMRequest(IAMRequestBase):
    def _raise_signature_does_not_match(self):
        if "BucketName" in self._data:
            raise BucketSignatureDoesNotMatchError(bucket=self._data["BucketName"])
        else:
            raise S3SignatureDoesNotMatchError()

    def _raise_invalid_access_key(self, reason):
        if reason == "InvalidToken":
            if "BucketName" in self._data:
                raise BucketInvalidTokenError(bucket=self._data["BucketName"])
            else:
                raise S3InvalidTokenError()
        else:
            if "BucketName" in self._data:
                raise BucketInvalidAccessKeyIdError(bucket=self._data["BucketName"])
            else:
                raise S3InvalidAccessKeyIdError()

    def _create_auth(self, credentials):
        return S3SigV4Auth(credentials, self._service, self._region)

    def _raise_access_denied(self):
        if "BucketName" in self._data:
            raise BucketAccessDeniedError(bucket=self._data["BucketName"])
        else:
            raise S3AccessDeniedError()


class IAMPolicy(object):
    def __init__(self, policy):
        if isinstance(policy, Policy):
            default_version = next(
                policy_version
                for policy_version in policy.versions
                if policy_version.is_default
            )
            policy_document = default_version.document
        elif isinstance(policy, str):
            policy_document = policy
        else:
            policy_document = policy["policy_document"]

        self._policy_json = json.loads(policy_document)

    def is_action_permitted(self, action):
        permitted = False
        if isinstance(self._policy_json["Statement"], list):
            for policy_statement in self._policy_json["Statement"]:
                iam_policy_statement = IAMPolicyStatement(policy_statement)
                permission_result = iam_policy_statement.is_action_permitted(action)
                if permission_result == PermissionResult.DENIED:
                    return permission_result
                elif permission_result == PermissionResult.PERMITTED:
                    permitted = True
        else:  # dict
            iam_policy_statement = IAMPolicyStatement(self._policy_json["Statement"])
            return iam_policy_statement.is_action_permitted(action)

        if permitted:
            return PermissionResult.PERMITTED
        else:
            return PermissionResult.NEUTRAL


class IAMPolicyStatement(object):
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
        pattern = "^{pattern}$".format(pattern=pattern)
        return re.match(pattern, string)


class PermissionResult(Enum):
    PERMITTED = 1
    DENIED = 2
    NEUTRAL = 3
