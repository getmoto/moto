from unittest import SkipTest, mock
import sure  # noqa # pylint: disable=unused-import

from collections import OrderedDict

from botocore.awsrequest import AWSPreparedRequest

from moto.core.responses import AWSServiceSpec, BaseResponse
from moto.core.responses import flatten_json_request_body
from moto import settings


def test_flatten_json_request_body():
    spec = AWSServiceSpec("data/emr/2009-03-31/service-2.json").input_spec("RunJobFlow")

    body = {
        "Name": "cluster",
        "Instances": {
            "Ec2KeyName": "ec2key",
            "InstanceGroups": [
                {"InstanceRole": "MASTER", "InstanceType": "m1.small"},
                {"InstanceRole": "CORE", "InstanceType": "m1.medium"},
            ],
            "Placement": {"AvailabilityZone": "us-east-1"},
        },
        "Steps": [
            {
                "HadoopJarStep": {
                    "Properties": [
                        {"Key": "k1", "Value": "v1"},
                        {"Key": "k2", "Value": "v2"},
                    ],
                    "Args": ["arg1", "arg2"],
                }
            }
        ],
        "Configurations": [
            {
                "Classification": "class",
                "Properties": {"propkey1": "propkey1", "propkey2": "propkey2"},
            },
            {"Classification": "anotherclass", "Properties": {"propkey3": "propkey3"}},
        ],
    }

    flat = flatten_json_request_body("", body, spec)
    flat["Name"].should.equal(body["Name"])
    flat["Instances.Ec2KeyName"].should.equal(body["Instances"]["Ec2KeyName"])
    for idx in range(2):
        flat[
            "Instances.InstanceGroups.member." + str(idx + 1) + ".InstanceRole"
        ].should.equal(body["Instances"]["InstanceGroups"][idx]["InstanceRole"])
        flat[
            "Instances.InstanceGroups.member." + str(idx + 1) + ".InstanceType"
        ].should.equal(body["Instances"]["InstanceGroups"][idx]["InstanceType"])
    flat["Instances.Placement.AvailabilityZone"].should.equal(
        body["Instances"]["Placement"]["AvailabilityZone"]
    )

    for idx in range(1):
        prefix = "Steps.member." + str(idx + 1) + ".HadoopJarStep"
        step = body["Steps"][idx]["HadoopJarStep"]
        i = 0
        while prefix + ".Properties.member." + str(i + 1) + ".Key" in flat:
            flat[prefix + ".Properties.member." + str(i + 1) + ".Key"].should.equal(
                step["Properties"][i]["Key"]
            )
            flat[prefix + ".Properties.member." + str(i + 1) + ".Value"].should.equal(
                step["Properties"][i]["Value"]
            )
            i += 1
        i = 0
        while prefix + ".Args.member." + str(i + 1) in flat:
            flat[prefix + ".Args.member." + str(i + 1)].should.equal(step["Args"][i])
            i += 1

    for idx in range(2):
        flat["Configurations.member." + str(idx + 1) + ".Classification"].should.equal(
            body["Configurations"][idx]["Classification"]
        )

        props = {}
        i = 1
        keyfmt = "Configurations.member.{0}.Properties.entry.{1}"
        key = keyfmt.format(idx + 1, i)
        while key + ".key" in flat:
            props[flat[key + ".key"]] = flat[key + ".value"]
            i += 1
            key = keyfmt.format(idx + 1, i)
        props.should.equal(body["Configurations"][idx]["Properties"])


def test_parse_qs_unicode_decode_error():
    body = b'{"key": "%D0"}, "C": "#0 = :0"}'
    request = AWSPreparedRequest("GET", "http://request", {"foo": "bar"}, body, False)
    BaseResponse().setup_class(request, request.url, request.headers)


def test_get_params():
    subject = BaseResponse()
    subject.querystring = OrderedDict(
        [
            ("Action", ["CreateRule"]),
            ("Version", ["2015-12-01"]),
            (
                "ListenerArn",
                [
                    "arn:aws:elasticloadbalancing:us-east-1:1:listener/my-lb/50dc6c495c0c9188/80139731473870416"
                ],
            ),
            ("Priority", ["100"]),
            ("Conditions.member.1.Field", ["http-header"]),
            ("Conditions.member.1.HttpHeaderConfig.HttpHeaderName", ["User-Agent"]),
            ("Conditions.member.1.HttpHeaderConfig.Values.member.2", ["curl"]),
            ("Conditions.member.1.HttpHeaderConfig.Values.member.1", ["Mozilla"]),
            ("Actions.member.1.FixedResponseConfig.StatusCode", ["200"]),
            ("Actions.member.1.FixedResponseConfig.ContentType", ["text/plain"]),
            ("Actions.member.1.Type", ["fixed-response"]),
        ]
    )

    result = subject._get_params()

    result.should.equal(
        {
            "Action": "CreateRule",
            "Version": "2015-12-01",
            "ListenerArn": "arn:aws:elasticloadbalancing:us-east-1:1:listener/my-lb/50dc6c495c0c9188/80139731473870416",
            "Priority": "100",
            "Conditions": [
                {
                    "Field": "http-header",
                    "HttpHeaderConfig": {
                        "HttpHeaderName": "User-Agent",
                        "Values": ["Mozilla", "curl"],
                    },
                }
            ],
            "Actions": [
                {
                    "Type": "fixed-response",
                    "FixedResponseConfig": {
                        "StatusCode": "200",
                        "ContentType": "text/plain",
                    },
                }
            ],
        }
    )


def test_get_dict_list_params():
    subject = BaseResponse()
    subject.querystring = OrderedDict(
        [
            ("Action", ["CreateDBCluster"]),
            ("Version", ["2014-10-31"]),
            ("VpcSecurityGroupIds.VpcSecurityGroupId.1", ["sg-123"]),
            ("VpcSecurityGroupIds.VpcSecurityGroupId.2", ["sg-456"]),
            ("VpcSecurityGroupIds.VpcSecurityGroupId.3", ["sg-789"]),
        ]
    )

    # TODO: extend test and logic such that we can call subject._get_params() directly here
    result = subject._get_multi_param_dict("VpcSecurityGroupIds")

    result.should.equal({"VpcSecurityGroupId": ["sg-123", "sg-456", "sg-789"]})


def test_response_environment_preserved_by_type():
    """Ensure Jinja environment is cached by response type."""

    class ResponseA(BaseResponse):
        pass

    class ResponseB(BaseResponse):
        pass

    resp_a = ResponseA()
    another_resp_a = ResponseA()
    resp_b = ResponseB()

    assert resp_a.environment is another_resp_a.environment
    assert resp_b.environment is not resp_a.environment

    source_1 = "template"
    source_2 = "amother template"

    assert not resp_a.contains_template(BaseResponse._make_template_id(source_1))
    resp_a.response_template(source_1)
    assert resp_a.contains_template(BaseResponse._make_template_id(source_1))

    assert not resp_a.contains_template(BaseResponse._make_template_id(source_2))
    resp_a.response_template(source_2)
    assert resp_a.contains_template(BaseResponse._make_template_id(source_2))

    assert not resp_b.contains_template(BaseResponse._make_template_id(source_1))
    assert not resp_b.contains_template(BaseResponse._make_template_id(source_2))

    assert another_resp_a.contains_template(BaseResponse._make_template_id(source_1))
    assert another_resp_a.contains_template(BaseResponse._make_template_id(source_2))

    resp_a_new_instance = ResponseA()
    assert resp_a_new_instance.contains_template(
        BaseResponse._make_template_id(source_1)
    )
    assert resp_a_new_instance.contains_template(
        BaseResponse._make_template_id(source_2)
    )


@mock.patch(
    "moto.core.responses.settings.PRETTIFY_RESPONSES",
    new_callable=mock.PropertyMock(return_value=True),
)
def test_jinja_render_prettify(m_env_var):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "It is not possible to set the environment variable in server mode"
        )
    response = BaseResponse()
    TEMPLATE = """<TestTemplate><ResponseText>Test text</ResponseText></TestTemplate>"""
    expected_output = '<?xml version="1.0" ?>\n<TestTemplate>\n\t<ResponseText>Test text</ResponseText>\n</TestTemplate>'
    template = response.response_template(TEMPLATE)
    xml_string = template.render()
    assert xml_string == expected_output
    assert m_env_var
