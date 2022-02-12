import sure  # noqa # pylint: disable=unused-import


from moto.ssm.utils import convert_to_tree, convert_to_params

SOURCE_PARAMS = [
    {
        "ARN": "arn:aws:ssm:us-west-1::parameter/aws/service/global-infrastructure/regions/af-south-1",
        "DataType": "text",
        "Name": "/aws/service/global-infrastructure/regions/af-south-1",
        "Type": "String",
        "Value": "af-south-1",
        "Version": 1,
    },
    {
        "ARN": "arn:aws:ssm:us-west-1::parameter/aws/service/global-infrastructure/regions/ap-northeast-2",
        "DataType": "text",
        "Name": "/aws/service/global-infrastructure/regions/ap-northeast-2",
        "Type": "String",
        "Value": "ap-northeast-2",
        "Version": 1,
    },
    {
        "ARN": "arn:aws:ssm:us-west-1::parameter/aws/service/global-infrastructure/regions/cn-north-1",
        "DataType": "text",
        "Name": "/aws/service/global-infrastructure/regions/cn-north-1",
        "Type": "String",
        "Value": "cn-north-1",
        "Version": 1,
    },
    {
        "ARN": "arn:aws:ssm:us-west-1::parameter/aws/service/global-infrastructure/regions/ap-northeast-2/services/codestar-notifications",
        "DataType": "text",
        "Name": "/aws/service/global-infrastructure/regions/ap-northeast-2/services/codestar-notifications",
        "Type": "String",
        "Value": "codestar-notifications",
        "Version": 1,
    },
]

EXPECTED_TREE = {
    "aws": {
        "service": {
            "global-infrastructure": {
                "regions": {
                    "af-south-1": {"Value": "af-south-1"},
                    "cn-north-1": {"Value": "cn-north-1"},
                    "ap-northeast-2": {
                        "Value": "ap-northeast-2",
                        "services": {
                            "codestar-notifications": {
                                "Value": "codestar-notifications"
                            }
                        },
                    },
                }
            }
        }
    }
}

CONVERTED_PARAMS = [
    {
        "Name": "/aws/service/global-infrastructure/regions/af-south-1",
        "Value": "af-south-1",
    },
    {
        "Name": "/aws/service/global-infrastructure/regions/cn-north-1",
        "Value": "cn-north-1",
    },
    {
        "Name": "/aws/service/global-infrastructure/regions/ap-northeast-2",
        "Value": "ap-northeast-2",
    },
    {
        "Name": "/aws/service/global-infrastructure/regions/ap-northeast-2/services/codestar-notifications",
        "Value": "codestar-notifications",
    },
]


def test_convert_to_tree():
    tree = convert_to_tree(SOURCE_PARAMS)

    tree.should.equal(EXPECTED_TREE)


def test_convert_to_params():
    actual = convert_to_params(EXPECTED_TREE)
    actual.should.have.length_of(len(CONVERTED_PARAMS))
    for param in CONVERTED_PARAMS:
        actual.should.contain(param)


def test_input_is_correct():
    """
    Test input should match
    """
    for src in SOURCE_PARAMS:
        minimized_src = {"Name": src["Name"], "Value": src["Value"]}
        CONVERTED_PARAMS.should.contain(minimized_src)
