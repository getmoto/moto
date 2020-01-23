from __future__ import unicode_literals

import unittest
import json

from moto.awslambda.policy import Policy


class MockLambdaFunction:
    def __init__(self, arn):
        self.function_arn = arn
        self.policy = None


class TC:
    def __init__(self, lambda_arn, statement, expected):
        self.statement = statement
        self.expected = expected
        self.fn = MockLambdaFunction(lambda_arn)
        self.policy = Policy(self.fn)

    def Run(self, parent):
        self.policy.add_statement(json.dumps(self.statement))
        parent.assertDictEqual(self.expected, self.policy.statements[0])

        sid = self.statement.get("StatementId", None)
        if sid == None:
            raise "TestCase.statement does not contain StatementId"

        self.policy.del_statement(sid)
        parent.assertEqual([], self.policy.statements)


class TestPolicy(unittest.TestCase):
    def test(self):
        tt = [
            TC(
                # lambda_arn
                "arn",
                {  # statement
                    "StatementId": "statement0",
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": "events.amazonaws.com",
                },
                {  # expected
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Effect": "Allow",
                    "Resource": "arn:$LATEST",
                    "Sid": "statement0",
                },
            ),
            TC(
                # lambda_arn
                "arn",
                {  # statement
                    "StatementId": "statement1",
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": "events.amazonaws.com",
                    "SourceArn": "arn:aws:events:us-east-1:111111111111:rule/rule_name",
                },
                {
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Effect": "Allow",
                    "Resource": "arn:$LATEST",
                    "Sid": "statement1",
                    "Condition": {
                        "ArnLike": {
                            "AWS:SourceArn": "arn:aws:events:us-east-1:111111111111:rule/rule_name"
                        }
                    },
                },
            ),
            TC(
                # lambda_arn
                "arn",
                {  # statement
                    "StatementId": "statement2",
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": "events.amazonaws.com",
                    "SourceAccount": "111111111111",
                },
                {  # expected
                    "Action": "lambda:InvokeFunction",
                    "FunctionName": "function_name",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Effect": "Allow",
                    "Resource": "arn:$LATEST",
                    "Sid": "statement2",
                    "Condition": {
                        "StringEquals": {"AWS:SourceAccount": "111111111111"}
                    },
                },
            ),
        ]

        for tc in tt:
            tc.Run(self)
