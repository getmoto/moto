import json

import pytest

from moto.ecr.exceptions import InvalidParameterException
from moto.ecr.policy_validation import EcrLifecyclePolicyValidator


def test_validate():
    # given
    policy = {
        "rules": [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            },
            {
                "rulePriority": 2,
                "description": "test policy",
                "selection": {
                    "tagStatus": "tagged",
                    "tagPrefixList": ["3.9"],
                    "countType": "sinceImagePushed",
                    "countUnit": "days",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            },
        ]
    }

    # when/then
    validator = EcrLifecyclePolicyValidator(json.dumps(policy))
    validator.validate()


@pytest.mark.parametrize(
    "policy",
    [
        "some invalid input",
        [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            }
        ],
    ],
    ids=["not_json", "not_dict"],
)
def test_validate_error_parse(policy):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(json.dumps(policy))
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert (
        ex.message
        == "Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: 'Lifecycle policy validation failure: Could not map policyString into LifecyclePolicy.'"
    )


@pytest.mark.parametrize(
    "policy",
    [
        {"no_rules": "test"},
        {
            "rules": {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            },
        },
    ],
    ids=["no_rules", "not_list"],
)
def test_validate_error_extract_rules(policy):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(json.dumps(policy))
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert (
        ex.message
        == "Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: 'Lifecycle policy validation failure: object has missing required properties ([\"rules\"])'"
    )


@pytest.mark.parametrize("rule", ["not_dict"], ids=["not_dict"])
def test_validate_error_rule_type(rule):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(json.dumps({"rules": [rule]}))
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert ex.message == (
        "Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: "
        "'Lifecycle policy validation failure: "
        f'instance type ({type(rule)}) does not match any allowed primitive type (allowed: ["object"])\''
    )


@pytest.mark.parametrize(
    ["rule", "error_msg"],
    [
        [
            {
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
            },
            'object has missing required properties (["rulePriority"])\'',
        ],
        [
            {
                "rulePriority": 1,
                "description": "test policy",
                "action": {"type": "expire"},
            },
            'object has missing required properties (["selection"])\'',
        ],
        [
            {
                "rulePriority": 1,
                "description": "test policy",
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
            },
            'object has missing required properties (["action"])\'',
        ],
        [
            {
                "rulePriority": 1,
                "selection": {
                    "tagStatus": "untagged",
                    "countType": "imageCountMoreThan",
                    "countNumber": 30,
                },
                "action": {"type": "expire"},
                "unknown": 123,
            },
            'object instance has properties which are not allowed by the schema: (["unknown"])\'',
        ],
    ],
    ids=["missing_rulePriority", "missing_selection", "missing_action", "unknown"],
)
def test_validate_error_rule_properties(rule, error_msg):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(json.dumps({"rules": [rule]}))
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert (
        ex.message
        == f"Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: 'Lifecycle policy validation failure: {error_msg}"
    )


@pytest.mark.parametrize(
    ["action", "error_msg"],
    [
        [{}, 'object has missing required properties (["type"])\''],
        [
            {"type": "expire", "unknown": 123},
            (
                "object instance has properties "
                'which are not allowed by the schema: (["unknown"])\''
            ),
        ],
        [
            {"type": "keep"},
            (
                "instance value (keep) not found in enum "
                ':(possible values: ["expire"])\''
            ),
        ],
    ],
    ids=["missing_type", "unknown", "unknown_type_value"],
)
def test_validate_error_action_properties(action, error_msg):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(
            json.dumps(
                {
                    "rules": [
                        {
                            "rulePriority": 1,
                            "selection": {
                                "tagStatus": "untagged",
                                "countType": "imageCountMoreThan",
                                "countNumber": 30,
                            },
                            "action": action,
                        }
                    ]
                }
            )
        )
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert (
        ex.message
        == f"Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: 'Lifecycle policy validation failure: {error_msg}"
    )


@pytest.mark.parametrize(
    ["selection", "error_msg"],
    [
        [
            {"countType": "imageCountMoreThan", "countNumber": 30},
            'object has missing required properties (["tagStatus"])\'',
        ],
        [
            {"tagStatus": "untagged", "countNumber": 30},
            'object has missing required properties (["countType"])\'',
        ],
        [
            {"tagStatus": "untagged", "countType": "imageCountMoreThan"},
            'object has missing required properties (["countNumber"])\'',
        ],
        [
            {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": 30,
                "unknown": 123,
            },
            (
                "object instance has properties "
                'which are not allowed by the schema: (["unknown"])\''
            ),
        ],
        [
            {
                "tagStatus": "unknown",
                "countType": "imageCountMoreThan",
                "countNumber": 30,
            },
            (
                "instance value (unknown) not found in enum "
                ':(possible values: ["any", "tagged", "untagged"])\''
            ),
        ],
        [
            {"tagStatus": "untagged", "countType": "unknown", "countNumber": 30},
            "instance failed to match exactly one schema (matched 0 out of 2)",
        ],
        [
            {
                "tagStatus": "untagged",
                "countType": "sinceImagePushed",
                "countUnit": "unknown",
                "countNumber": 30,
            },
            (
                "instance value (unknown) not found in enum "
                ':(possible values: ["days"])\''
            ),
        ],
        [
            {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": 0,
            },
            (
                "numeric instance is lower than the required minimum "
                "(minimum: 1, found: 0)"
            ),
        ],
        [
            {
                "tagStatus": "untagged",
                "countType": "imageCountMoreThan",
                "countNumber": -1,
            },
            (
                "numeric instance is lower than the required minimum "
                "(minimum: 1, found: -1)"
            ),
        ],
    ],
    ids=[
        "missing_tagStatus",
        "missing_countType",
        "missing_countNumber",
        "unknown",
        "unknown_tagStatus_value",
        "unknown_countType_value",
        "unknown_countUnit_value",
        "zero_countNumber_value",
        "negative_countNumber_value",
    ],
)
def test_validate_error_selection_properties(selection, error_msg):
    # given

    # when
    with pytest.raises(InvalidParameterException) as e:
        validator = EcrLifecyclePolicyValidator(
            json.dumps(
                {
                    "rules": [
                        {
                            "rulePriority": 1,
                            "selection": selection,
                            "action": {"type": "expire"},
                        }
                    ]
                }
            )
        )
        validator.validate()

    # then
    ex = e.value
    assert ex.code == 400
    assert ex.error_type == "InvalidParameterException"
    assert (
        ex.message
        == f"Invalid parameter at 'LifecyclePolicyText' failed to satisfy constraint: 'Lifecycle policy validation failure: {error_msg}"
    )
