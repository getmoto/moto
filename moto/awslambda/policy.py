from __future__ import unicode_literals

import json
import uuid

from six import string_types

from moto.awslambda.exceptions import PreconditionFailedException


class Policy:
    def __init__(self, parent):
        self.revision = str(uuid.uuid4())
        self.statements = []
        self.parent = parent

    def wire_format(self):
        p = self.get_policy()
        p["Policy"] = json.dumps(p["Policy"])
        return json.dumps(p)

    def get_policy(self):
        return {
            "Policy": {
                "Version": "2012-10-17",
                "Id": "default",
                "Statement": self.statements,
            },
            "RevisionId": self.revision,
        }

    # adds the raw JSON statement to the policy
    def add_statement(self, raw):
        policy = json.loads(raw, object_hook=self.decode_policy)
        if len(policy.revision) > 0 and self.revision != policy.revision:
            raise PreconditionFailedException(
                "The RevisionId provided does not match the latest RevisionId"
                " for the Lambda function or alias. Call the GetFunction or the GetAlias API to retrieve"
                " the latest RevisionId for your resource."
            )
        self.statements.append(policy.statements[0])
        self.revision = str(uuid.uuid4())

    # removes the statement that matches 'sid' from the policy
    def del_statement(self, sid, revision=""):
        if len(revision) > 0 and self.revision != revision:
            raise PreconditionFailedException(
                "The RevisionId provided does not match the latest RevisionId"
                " for the Lambda function or alias. Call the GetFunction or the GetAlias API to retrieve"
                " the latest RevisionId for your resource."
            )
        for statement in self.statements:
            if "Sid" in statement and statement["Sid"] == sid:
                self.statements.remove(statement)

    # converts AddPermission request to PolicyStatement
    # https://docs.aws.amazon.com/lambda/latest/dg/API_AddPermission.html
    def decode_policy(self, obj):
        # import pydevd
        # pydevd.settrace("localhost", port=5678)
        policy = Policy(self.parent)
        policy.revision = obj.get("RevisionId", "")

        # set some default values if these keys are not set
        self.ensure_set(obj, "Effect", "Allow")
        self.ensure_set(obj, "Resource", self.parent.function_arn + ":$LATEST")
        self.ensure_set(obj, "StatementId", str(uuid.uuid4()))

        # transform field names and values
        self.transform_property(obj, "StatementId", "Sid", self.nop_formatter)
        self.transform_property(obj, "Principal", "Principal", self.principal_formatter)

        self.transform_property(
            obj, "SourceArn", "SourceArn", self.source_arn_formatter
        )
        self.transform_property(
            obj, "SourceAccount", "SourceAccount", self.source_account_formatter
        )

        # remove RevisionId and EventSourceToken if they are set
        self.remove_if_set(obj, ["RevisionId", "EventSourceToken"])

        # merge conditional statements into a single map under the Condition key
        self.condition_merge(obj)

        # append resulting statement to policy.statements
        policy.statements.append(obj)

        return policy

    def nop_formatter(self, obj):
        return obj

    def ensure_set(self, obj, key, value):
        if key not in obj:
            obj[key] = value

    def principal_formatter(self, obj):
        if isinstance(obj, string_types):
            if obj.endswith(".amazonaws.com"):
                return {"Service": obj}
            if obj.endswith(":root"):
                return {"AWS": obj}
        return obj

    def source_account_formatter(self, obj):
        return {"StringEquals": {"AWS:SourceAccount": obj}}

    def source_arn_formatter(self, obj):
        return {"ArnLike": {"AWS:SourceArn": obj}}

    def transform_property(self, obj, old_name, new_name, formatter):
        if old_name in obj:
            obj[new_name] = formatter(obj[old_name])
            if new_name != old_name:
                del obj[old_name]

    def remove_if_set(self, obj, keys):
        for key in keys:
            if key in obj:
                del obj[key]

    def condition_merge(self, obj):
        if "SourceArn" in obj:
            if "Condition" not in obj:
                obj["Condition"] = {}
            obj["Condition"].update(obj["SourceArn"])
            del obj["SourceArn"]

        if "SourceAccount" in obj:
            if "Condition" not in obj:
                obj["Condition"] = {}
            obj["Condition"].update(obj["SourceAccount"])
            del obj["SourceAccount"]
