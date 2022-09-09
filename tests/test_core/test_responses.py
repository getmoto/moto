import io

# import sure  # noqa # pylint: disable=unused-import

from collections import OrderedDict

from botocore.awsrequest import AWSPreparedRequest

from moto.core.responses import AWSServiceSpec, BaseResponse
from moto.core.responses import flatten_json_request_body

from moto import settings, mock_ec2
from tests import EXAMPLE_AMI_ID
from unittest import SkipTest, mock
import boto3
import requests
import json


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


@mock_ec2
@mock.patch(
    "moto.core.responses.settings.ENABLE_RECORDING",
    new_callable=mock.PropertyMock(return_value=True),
)
@mock.patch("moto.core.responses.open", return_value=mock.MagicMock(spec=io.IOBase))
def test_recording(m_open, m_setting):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "It is not possible to set the environment variable in server mode"
        )
    ec2 = boto3.resource("ec2", "us-east-1")
    expected_data = '{"module": "moto.ec2.responses", "response_type": "EC2Response", "response_headers": {"server": "amazon.com"}, "region": "us-east-1", "body": "Action=RunInstances&Version=2016-11-15&ImageId=ami-12c6146b&MinCount=1&MaxCount=1&ClientToken=0ee5e722-d843-40f8-9f7b-62c92bb73d94", "uri_match": null, "querystring": {"Action": ["RunInstances"], "Version": ["2016-11-15"], "ImageId": ["ami-12c6146b"], "MinCount": ["1"], "MaxCount": ["1"], "ClientToken": ["0ee5e722-d843-40f8-9f7b-62c92bb73d94"]}}'

    ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        ClientToken="0ee5e722-d843-40f8-9f7b-62c92bb73d94",
    )

    file_handle = m_open.return_value.__enter__.return_value
    assert file_handle.write.mock_calls[0][1][0] == expected_data
    assert m_setting is True


@mock_ec2
@mock.patch(
    "moto.core.responses.BaseResponse._record_to_file",
)
def test_start_stop_recording(m_record):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "mock patch does not work in server mode"
        )
    ec2 = boto3.resource("ec2", "us-east-1")
    BASE_URL = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )

    requests.get("{0}/moto-api/start-recording".format(BASE_URL))
    ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        ClientToken="0ee5e722-d843-40f8-9f7b-62c92bb73d94",
    )

    requests.get("{0}/moto-api/stop-recording".format(BASE_URL))
    ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        ClientToken="0ee5e722-d843-40f8-9f7b-62c92bb73d94",
    )

    assert m_record.call_count == 1


@mock_ec2
@mock.patch("moto.core.responses.open", return_value=mock.MagicMock(spec=io.IOBase))
def test_replay_recording(m_open):
    boto3.resource("ec2", "us-east-1")
    BASE_URL = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )

    recorded_data = '{"module": "moto.ec2.responses", "response_type": "EC2Response", "response_headers": {"server": "amazon.com"}, "region": "us-east-1", "body": "Action=RunInstances&Version=2016-11-15&ImageId=ami-12c6146b&MinCount=1&MaxCount=1&ClientToken=0ee5e722-d843-40f8-9f7b-62c92bb73d94", "uri_match": null, "querystring": {"Action": ["RunInstances"], "Version": ["2016-11-15"], "ImageId": ["ami-12c6146b"], "MinCount": ["1"], "MaxCount": ["1"], "ClientToken": ["0ee5e722-d843-40f8-9f7b-62c92bb73d94"]}}'
    file_handle = m_open.return_value.__enter__.return_value
    file_handle.readlines.return_value = [recorded_data]

    requests.get("{0}/moto-api/replay-recording".format(BASE_URL))

    data_response = requests.get("{0}/moto-api/data.json".format(BASE_URL))
    assert len(json.loads(data_response.text)["ec2"]["Instance"]) == 1


@mock_ec2
@mock.patch("moto.core.responses.open", return_value=mock.MagicMock(spec=io.IOBase))
def test_download_recording(m_open):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "mock patch does not work in server mode"
        )
    boto3.resource("ec2", "us-east-1")
    BASE_URL = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )
    recorded_data = '{"module": "moto.ec2.responses", "response_type": "EC2Response", "response_headers": {"server": "amazon.com"}, "region": "us-east-1", "body": "Action=RunInstances&Version=2016-11-15&ImageId=ami-12c6146b&MinCount=1&MaxCount=1&ClientToken=0ee5e722-d843-40f8-9f7b-62c92bb73d94", "uri_match": null, "querystring": {"Action": ["RunInstances"], "Version": ["2016-11-15"], "ImageId": ["ami-12c6146b"], "MinCount": ["1"], "MaxCount": ["1"], "ClientToken": ["0ee5e722-d843-40f8-9f7b-62c92bb73d94"]}}'
    file_handle = m_open.return_value.__enter__.return_value
    file_handle.read.return_value = recorded_data

    data_response = requests.get("{0}/moto-api/download-recording".format(BASE_URL))

    assert data_response.text == recorded_data


@mock_ec2
@mock.patch(
    "moto.core.responses.open",
    return_value=mock.MagicMock(spec=io.IOBase),
)
def test_upload_recording(m_open):
    if settings.TEST_SERVER_MODE:
        raise SkipTest(
            "mock patch does not work in server mode"
        )
    boto3.resource("ec2", "us-east-1")
    BASE_URL = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )
    recorded_data = b'{"module": "moto.ec2.responses", "response_type": "EC2Response", "response_headers": {"server": "amazon.com"}, "region": "us-east-1", "body": "Action=RunInstances&Version=2016-11-15&ImageId=ami-12c6146b&MinCount=1&MaxCount=1&ClientToken=0ee5e722-d843-40f8-9f7b-62c92bb73d94", "uri_match": null, "querystring": {"Action": ["RunInstances"], "Version": ["2016-11-15"], "ImageId": ["ami-12c6146b"], "MinCount": ["1"], "MaxCount": ["1"], "ClientToken": ["0ee5e722-d843-40f8-9f7b-62c92bb73d94"]}}'

    file_handle = m_open.return_value.__enter__.return_value
    file_handle.read.return_value = recorded_data
    requests.get("{0}/moto-api/upload-recording".format(BASE_URL), data=recorded_data)

    assert file_handle.write.mock_calls[0][1][0] == recorded_data


@mock_ec2
def test_set_seed():
    ec2 = boto3.resource("ec2", "us-east-1")
    BASE_URL = (
        "http://localhost:5000"
        if settings.TEST_SERVER_MODE
        else "http://motoapi.amazonaws.com"
    )

    requests.get(
        "{0}/moto-api/set-seed?seed=42".format(BASE_URL),
    )
    reservation_1 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        ClientToken="0ee5e722-d843-40f8-9f7b-62c92bb73d94",
    )

    requests.get("{0}/moto-api/set-seed?seed=42".format(BASE_URL))
    reservation_2 = ec2.create_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        ClientToken="0ee5e722-d843-40f8-9f7b-62c92bb73d94",
    )

    assert reservation_1[0].id == reservation_2[0].id
