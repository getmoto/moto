import json
import re

from six import string_types

from moto.iam.exceptions import MalformedPolicyDocument


VALID_TOP_ELEMENTS = [
    "Version",
    "Id",
    "Statement",
    "Conditions"
]

VALID_VERSIONS = [
    "2008-10-17",
    "2012-10-17"
]

VALID_STATEMENT_ELEMENTS = [
    "Sid",
    "Action",
    "NotAction",
    "Resource",
    "NotResource",
    "Effect",
    "Condition"
]

VALID_EFFECTS = [
    "Allow",
    "Deny"
]

SERVICE_TYPE_REGION_INFORMATION_ERROR_ASSOCIATIONS = {
    "iam": 'IAM resource {resource} cannot contain region information.',
    "s3": 'Resource {resource} can not contain region information.'
}

VALID_RESOURCE_PATH_STARTING_VALUES = {
    "iam": {
        "values": ["user/", "federated-user/", "role/", "group/", "instance-profile/", "mfa/", "server-certificate/",
                   "policy/", "sms-mfa/", "saml-provider/", "oidc-provider/", "report/", "access-report/"],
        "error_message": 'IAM resource path must either be "*" or start with {values}.'
    }
}


class IAMPolicyDocumentValidator:

    def __init__(self, policy_document: str):
        self._policy_document: str = policy_document
        self._policy_json: dict = {}
        self._statements = []

    def validate(self):
        try:
            self._validate_syntax()
        except Exception:
            raise MalformedPolicyDocument("Syntax errors in policy.")
        try:
            self._validate_version()
        except Exception:
            raise MalformedPolicyDocument("Policy document must be version 2012-10-17 or greater.")
        try:
            self._validate_sid_uniqueness()
        except Exception:
            raise MalformedPolicyDocument("Statement IDs (SID) in a single policy must be unique.")
        try:
            self._validate_action_like_exist()
        except Exception:
            raise MalformedPolicyDocument("Policy statement must contain actions.")
        try:
            self._validate_resource_exist()
        except Exception:
            raise MalformedPolicyDocument("Policy statement must contain resources.")

        self._validate_resources_for_formats()
        self._validate_not_resources_for_formats()

        self._validate_actions_for_prefixes()
        self._validate_not_actions_for_prefixes()

    def _validate_syntax(self):
        self._policy_json = json.loads(self._policy_document)
        assert isinstance(self._policy_json, dict)
        self._validate_top_elements()
        self._validate_version_syntax()
        self._validate_id_syntax()
        self._validate_statements_syntax()

    def _validate_top_elements(self):
        top_elements = self._policy_json.keys()
        for element in top_elements:
            assert element in VALID_TOP_ELEMENTS

    def _validate_version_syntax(self):
        if "Version" in self._policy_json:
            assert self._policy_json["Version"] in VALID_VERSIONS

    def _validate_version(self):
        assert self._policy_json["Version"] == "2012-10-17"

    def _validate_sid_uniqueness(self):
        sids = []
        for statement in self._statements:
            if "Sid" in statement:
                assert statement["Sid"] not in sids
                sids.append(statement["Sid"])

    def _validate_statements_syntax(self):
        assert "Statement" in self._policy_json
        assert isinstance(self._policy_json["Statement"], (dict, list))

        if isinstance(self._policy_json["Statement"], dict):
            self._statements.append(self._policy_json["Statement"])
        else:
            self._statements += self._policy_json["Statement"]

        assert self._statements
        for statement in self._statements:
            self._validate_statement_syntax(statement)

    @staticmethod
    def _validate_statement_syntax(statement):
        assert isinstance(statement, dict)
        for statement_element in statement.keys():
            assert statement_element in VALID_STATEMENT_ELEMENTS

        assert ("Resource" not in statement or "NotResource" not in statement)
        assert ("Action" not in statement or "NotAction" not in statement)

        IAMPolicyDocumentValidator._validate_effect_syntax(statement)
        IAMPolicyDocumentValidator._validate_action_syntax(statement)
        IAMPolicyDocumentValidator._validate_not_action_syntax(statement)
        IAMPolicyDocumentValidator._validate_resource_syntax(statement)
        IAMPolicyDocumentValidator._validate_not_resource_syntax(statement)
        IAMPolicyDocumentValidator._validate_condition_syntax(statement)
        IAMPolicyDocumentValidator._validate_sid_syntax(statement)

    @staticmethod
    def _validate_effect_syntax(statement):
        assert "Effect" in statement
        assert isinstance(statement["Effect"], string_types)
        assert statement["Effect"].lower() in [allowed_effect.lower() for allowed_effect in VALID_EFFECTS]

    @staticmethod
    def _validate_action_syntax(statement):
        IAMPolicyDocumentValidator._validate_string_or_list_of_strings_syntax(statement, "Action")

    @staticmethod
    def _validate_not_action_syntax(statement):
        IAMPolicyDocumentValidator._validate_string_or_list_of_strings_syntax(statement, "NotAction")

    @staticmethod
    def _validate_resource_syntax(statement):
        IAMPolicyDocumentValidator._validate_string_or_list_of_strings_syntax(statement, "Resource")

    @staticmethod
    def _validate_not_resource_syntax(statement):
        IAMPolicyDocumentValidator._validate_string_or_list_of_strings_syntax(statement, "NotResource")

    @staticmethod
    def _validate_string_or_list_of_strings_syntax(statement, key):
        if key in statement:
            assert isinstance(statement[key], (string_types, list))
            if isinstance(statement[key], list):
                for resource in statement[key]:
                    assert isinstance(resource, string_types)

    @staticmethod
    def _validate_condition_syntax(statement):
        if "Condition" in statement:
            assert isinstance(statement["Condition"], dict)
            for condition_key, condition_value in statement["Condition"].items():
                assert isinstance(condition_value, dict)
                for condition_data_key, condition_data_value in condition_value.items():
                    assert isinstance(condition_data_value, (list, string_types))

    @staticmethod
    def _validate_sid_syntax(statement):
        if "Sid" in statement:
            assert isinstance(statement["Sid"], string_types)

    def _validate_id_syntax(self):
        if "Id" in self._policy_json:
            assert isinstance(self._policy_json["Id"], string_types)

    def _validate_resource_exist(self):
        for statement in self._statements:
            assert ("Resource" in statement or "NotResource" in statement)
            if "Resource" in statement and isinstance(statement["Resource"], list):
                assert statement["Resource"]
            elif "NotResource" in statement and isinstance(statement["NotResource"], list):
                assert statement["NotResource"]

    def _validate_action_like_exist(self):
        for statement in self._statements:
            assert ("Action" in statement or "NotAction" in statement)
            if "Action" in statement and isinstance(statement["Action"], list):
                assert statement["Action"]
            elif "NotAction" in statement and isinstance(statement["NotAction"], list):
                assert statement["NotAction"]

    def _validate_actions_for_prefixes(self):
        self._validate_action_like_for_prefixes("Action")

    def _validate_not_actions_for_prefixes(self):
        self._validate_action_like_for_prefixes("NotAction")

    def _validate_action_like_for_prefixes(self, key):
        for statement in self._statements:
            if key in statement:
                if isinstance(statement[key], string_types):
                    self._validate_action_prefix(statement[key])
                else:
                    for action in statement[key]:
                        self._validate_action_prefix(action)

    @staticmethod
    def _validate_action_prefix(action):
        action_parts = action.split(":")
        if len(action_parts) == 1:
            raise MalformedPolicyDocument("Actions/Conditions must be prefaced by a vendor, e.g., iam, sdb, ec2, etc.")
        elif len(action_parts) > 2:
            raise MalformedPolicyDocument("Actions/Condition can contain only one colon.")

        vendor_pattern = re.compile(r'[^a-zA-Z0-9\-.]')
        if vendor_pattern.search(action_parts[0]):
            raise MalformedPolicyDocument("Vendor {vendor} is not valid".format(vendor=action_parts[0]))

    def _validate_resources_for_formats(self):
        self._validate_resource_like_for_formats("Resource")

    def _validate_not_resources_for_formats(self):
        self._validate_resource_like_for_formats("NotResource")

    def _validate_resource_like_for_formats(self, key):
        for statement in self._statements:
            if key in statement:
                if isinstance(statement[key], string_types):
                    self._validate_resource_format(statement[key])
                else:
                    for resource in statement[key]:
                        self._validate_resource_format(resource)

    @staticmethod
    def _validate_resource_format(resource):
        if resource != "*":
            resource_partitions = resource.partition(":")

            if resource_partitions[1] == "":
                raise MalformedPolicyDocument('Resource {resource} must be in ARN format or "*".'.format(resource=resource))

            resource_partitions = resource_partitions[2].partition(":")
            if resource_partitions[0] != "aws":
                remaining_resource_parts = resource_partitions[2].split(":")

                arn1 = remaining_resource_parts[0] if remaining_resource_parts[0] != "" else "*"
                arn2 = remaining_resource_parts[1] if len(remaining_resource_parts) > 1 else "*"
                arn3 = remaining_resource_parts[2] if len(remaining_resource_parts) > 2 else "*"
                arn4 = ":".join(remaining_resource_parts[3:]) if len(remaining_resource_parts) > 3 else "*"
                raise MalformedPolicyDocument(
                    'Partition "{partition}" is not valid for resource "arn:{partition}:{arn1}:{arn2}:{arn3}:{arn4}".'.format(
                        partition=resource_partitions[0],
                        arn1=arn1,
                        arn2=arn2,
                        arn3=arn3,
                        arn4=arn4
                    ))

            if resource_partitions[1] != ":":
                raise MalformedPolicyDocument("Resource vendor must be fully qualified and cannot contain regexes.")

            resource_partitions = resource_partitions[2].partition(":")

            service = resource_partitions[0]

            if service in SERVICE_TYPE_REGION_INFORMATION_ERROR_ASSOCIATIONS.keys() and not resource_partitions[2].startswith(":"):
                raise MalformedPolicyDocument(SERVICE_TYPE_REGION_INFORMATION_ERROR_ASSOCIATIONS[service].format(resource=resource))

            resource_partitions = resource_partitions[2].partition(":")
            resource_partitions = resource_partitions[2].partition(":")

            if service in VALID_RESOURCE_PATH_STARTING_VALUES.keys():
                valid_start = False
                for valid_starting_value in VALID_RESOURCE_PATH_STARTING_VALUES[service]["values"]:
                    if resource_partitions[2].startswith(valid_starting_value):
                        valid_start = True
                        break
                if not valid_start:
                    raise MalformedPolicyDocument(VALID_RESOURCE_PATH_STARTING_VALUES[service]["error_message"].format(
                        values=", ".join(VALID_RESOURCE_PATH_STARTING_VALUES[service]["values"])
                    ))


