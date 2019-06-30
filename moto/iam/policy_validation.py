import json

from six import string_types

from moto.iam.exceptions import MalformedPolicyDocument


ALLOWED_TOP_ELEMENTS = [
    "Version",
    "Id",
    "Statement",
    "Conditions"
]

ALLOWED_VERSIONS = [
    "2008-10-17",
    "2012-10-17"
]

ALLOWED_STATEMENT_ELEMENTS = [
    "Sid",
    "Action",
    "NotAction",
    "Resource",
    "NotResource",
    "Effect",
    "Condition"
]

ALLOWED_EFFECTS = [
    "Allow",
    "Deny"
]


class IAMPolicyDocumentValidator:

    def __init__(self, policy_document):
        self._policy_document = policy_document
        self._policy_json = {}
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
            self._validate_resource_exist()
        except Exception:
            raise MalformedPolicyDocument("Policy statement must contain resources.")

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
            assert element in ALLOWED_TOP_ELEMENTS

    def _validate_version_syntax(self):
        if "Version" in self._policy_json:
            assert self._policy_json["Version"] in ALLOWED_VERSIONS

    def _validate_version(self):
        assert self._policy_json["Version"] == "2012-10-17"

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
            assert statement_element in ALLOWED_STATEMENT_ELEMENTS

        assert ("Resource" not in statement or "NotResource" not in statement)
        assert ("Action" not in statement or "NotAction" not in statement)

        IAMPolicyDocumentValidator._validate_effect_syntax(statement)
        IAMPolicyDocumentValidator._validate_resource_syntax(statement)
        IAMPolicyDocumentValidator._validate_not_resource_syntax(statement)
        IAMPolicyDocumentValidator._validate_condition_syntax(statement)
        IAMPolicyDocumentValidator._validate_sid_syntax(statement)

    @staticmethod
    def _validate_effect_syntax(statement):
        assert "Effect" in statement
        assert isinstance(statement["Effect"], string_types)
        assert statement["Effect"].lower() in [allowed_effect.lower() for allowed_effect in ALLOWED_EFFECTS]

    @staticmethod
    def _validate_resource_syntax(statement):
        IAMPolicyDocumentValidator._validate_resource_like_syntax(statement, "Resource")

    @staticmethod
    def _validate_not_resource_syntax(statement):
        IAMPolicyDocumentValidator._validate_resource_like_syntax(statement, "NotResource")

    @staticmethod
    def _validate_resource_like_syntax(statement, key):
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
        if "Id" in self._policy_document:
            assert isinstance(self._policy_document["Id"], string_types)

    def _validate_resource_exist(self):
        for statement in self._statements:
            assert "Resource" in statement

