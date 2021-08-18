from __future__ import unicode_literals

import json
import sure  # noqa
import boto3

from moto import mock_iot
from botocore.exceptions import ClientError
import pytest


def generate_thing_group_tree(iot_client, tree_dict, _parent=None):
    """
    Generates a thing group tree given the input tree structure.
    :param iot_client: the iot client for boto3
    :param tree_dict: dictionary with the key being the group_name, and the value being a sub tree.
        tree_dict = {
            "group_name_1a":{
                "group_name_2a":{
                    "group_name_3a":{} or None
                },
            },
            "group_name_1b":{}
        }
    :return: a dictionary of created groups, keyed by group name
    """
    if tree_dict is None:
        tree_dict = {}
    created_dict = {}
    for group_name in tree_dict.keys():
        params = {"thingGroupName": group_name}
        if _parent:
            params["parentGroupName"] = _parent
        created_group = iot_client.create_thing_group(**params)
        created_dict[group_name] = created_group
        subtree_dict = generate_thing_group_tree(
            iot_client=iot_client, tree_dict=tree_dict[group_name], _parent=group_name
        )
        created_dict.update(created_dict)
        created_dict.update(subtree_dict)
    return created_dict


@mock_iot
def test_attach_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal("my-policy")


@mock_iot
def test_detach_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    res["policies"][0]["policyName"].should.equal("my-policy")

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_attached_policies(target=cert_arn)
    res.should.have.key("policies").which.should.be.empty


@mock_iot
def test_list_attached_policies():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    policies = client.list_attached_policies(target=cert["certificateArn"])
    policies["policies"].should.be.empty


@mock_iot
def test_policy_versions():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"

    policy = client.create_policy(policyName=policy_name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(json.dumps({}))
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy["defaultVersionId"]
    )

    policy1 = client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_1"}),
        setAsDefault=True,
    )
    policy1.should.have.key("policyArn").which.should_not.be.none
    policy1.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy1.should.have.key("policyVersionId").which.should.equal("2")
    policy1.should.have.key("isDefaultVersion").which.should.equal(True)

    policy2 = client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_2"}),
        setAsDefault=False,
    )
    policy2.should.have.key("policyArn").which.should_not.be.none
    policy2.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_2"})
    )
    policy2.should.have.key("policyVersionId").which.should.equal("3")
    policy2.should.have.key("isDefaultVersion").which.should.equal(False)

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    policy3 = client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_3"}),
        setAsDefault=False,
    )
    policy3.should.have.key("policyArn").which.should_not.be.none
    policy3.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_3"})
    )
    policy3.should.have.key("policyVersionId").which.should.equal("4")
    policy3.should.have.key("isDefaultVersion").which.should.equal(False)

    policy4 = client.create_policy_version(
        policyName=policy_name,
        policyDocument=json.dumps({"version": "version_4"}),
        setAsDefault=False,
    )
    policy4.should.have.key("policyArn").which.should_not.be.none
    policy4.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_4"})
    )
    policy4.should.have.key("policyVersionId").which.should.equal("5")
    policy4.should.have.key("isDefaultVersion").which.should.equal(False)

    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(5)
    list(
        map(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    ).count(True).should.equal(1)
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    )
    default_policy[0].should.have.key("versionId").should.equal(
        policy1["policyVersionId"]
    )

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_1"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy1["policyVersionId"]
    )

    client.set_default_policy_version(
        policyName=policy_name, policyVersionId=policy4["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(5)
    list(
        map(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    ).count(True).should.equal(1)
    default_policy = list(
        filter(lambda item: item["isDefaultVersion"], policy_versions["policyVersions"])
    )
    default_policy[0].should.have.key("versionId").should.equal(
        policy4["policyVersionId"]
    )

    policy = client.get_policy(policyName=policy_name)
    policy.should.have.key("policyName").which.should.equal(policy_name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(
        json.dumps({"version": "version_4"})
    )
    policy.should.have.key("defaultVersionId").which.should.equal(
        policy4["policyVersionId"]
    )

    try:
        client.create_policy_version(
            policyName=policy_name,
            policyDocument=json.dumps({"version": "version_5"}),
            setAsDefault=False,
        )
        assert False, "Should have failed in previous call"
    except Exception as exception:
        exception.response["Error"]["Message"].should.equal(
            "The policy %s already has the maximum number of versions (5)" % policy_name
        )

    client.delete_policy_version(policyName=policy_name, policyVersionId="1")
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(4)

    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy1["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(3)
    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy2["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(2)

    client.delete_policy_version(
        policyName=policy_name, policyVersionId=policy3["policyVersionId"]
    )
    policy_versions = client.list_policy_versions(policyName=policy_name)
    policy_versions.should.have.key("policyVersions").which.should.have.length_of(1)

    # should fail as it"s the default policy. Should use delete_policy instead
    try:
        client.delete_policy_version(
            policyName=policy_name, policyVersionId=policy4["policyVersionId"]
        )
        assert False, "Should have failed in previous call"
    except Exception as exception:
        exception.response["Error"]["Message"].should.equal(
            "Cannot delete the default version of a policy"
        )


@mock_iot
def test_things():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    type_name = "my-type-name"

    # thing type
    thing_type = client.create_thing_type(thingTypeName=type_name)
    thing_type.should.have.key("thingTypeName").which.should.equal(type_name)
    thing_type.should.have.key("thingTypeArn")
    thing_type["thingTypeArn"].should.contain(type_name)

    res = client.list_thing_types()
    res.should.have.key("thingTypes").which.should.have.length_of(1)
    for thing_type in res["thingTypes"]:
        thing_type.should.have.key("thingTypeName").which.should_not.be.none

    thing_type = client.describe_thing_type(thingTypeName=type_name)
    thing_type.should.have.key("thingTypeName").which.should.equal(type_name)
    thing_type.should.have.key("thingTypeProperties")
    thing_type.should.have.key("thingTypeMetadata")
    thing_type.should.have.key("thingTypeArn")
    thing_type["thingTypeArn"].should.contain(type_name)

    # thing
    thing = client.create_thing(thingName=name, thingTypeName=type_name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")
    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(1)
    for thing in res["things"]:
        thing.should.have.key("thingName").which.should_not.be.none
        thing.should.have.key("thingArn").which.should_not.be.none

    thing = client.update_thing(
        thingName=name, attributePayload={"attributes": {"k1": "v1"}}
    )
    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(1)
    for thing in res["things"]:
        thing.should.have.key("thingName").which.should_not.be.none
        thing.should.have.key("thingArn").which.should_not.be.none
    res["things"][0]["attributes"].should.have.key("k1").which.should.equal("v1")

    thing = client.describe_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("defaultClientId")
    thing.should.have.key("thingTypeName")
    thing.should.have.key("attributes")
    thing.should.have.key("version")

    # delete thing
    client.delete_thing(thingName=name)
    res = client.list_things()
    res.should.have.key("things").which.should.have.length_of(0)

    # delete thing type
    client.delete_thing_type(thingTypeName=type_name)
    res = client.list_thing_types()
    res.should.have.key("thingTypes").which.should.have.length_of(0)


@mock_iot
def test_list_thing_types():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 100):
        client.create_thing_type(thingTypeName=str(i + 1))

    thing_types = client.list_thing_types()
    thing_types.should.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(50)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("1")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("50")

    thing_types = client.list_thing_types(nextToken=thing_types["nextToken"])
    thing_types.should.have.key("thingTypes").which.should.have.length_of(50)
    thing_types.should_not.have.key("nextToken")
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("51")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("100")


@mock_iot
def test_list_thing_types_with_typename_filter():
    client = boto3.client("iot", region_name="ap-northeast-1")

    client.create_thing_type(thingTypeName="thing")
    client.create_thing_type(thingTypeName="thingType")
    client.create_thing_type(thingTypeName="thingTypeName")
    client.create_thing_type(thingTypeName="thingTypeNameGroup")
    client.create_thing_type(thingTypeName="shouldNotFind")
    client.create_thing_type(thingTypeName="find me it shall not")

    thing_types = client.list_thing_types(thingTypeName="thing")
    thing_types.should_not.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(4)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("thing")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("thingTypeNameGroup")

    thing_types = client.list_thing_types(thingTypeName="thingTypeName")
    thing_types.should_not.have.key("nextToken")
    thing_types.should.have.key("thingTypes").which.should.have.length_of(2)
    thing_types["thingTypes"][0]["thingTypeName"].should.equal("thingTypeName")
    thing_types["thingTypes"][-1]["thingTypeName"].should.equal("thingTypeNameGroup")


@mock_iot
def test_list_things_with_next_token():
    client = boto3.client("iot", region_name="ap-northeast-1")

    for i in range(0, 200):
        client.create_thing(thingName=str(i + 1))

    things = client.list_things()
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("1")
    things["things"][0]["thingArn"].should.equal("arn:aws:iot:ap-northeast-1:1:thing/1")
    things["things"][-1]["thingName"].should.equal("50")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/50"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("51")
    things["things"][0]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/51"
    )
    things["things"][-1]["thingName"].should.equal("100")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/100"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("101")
    things["things"][0]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/101"
    )
    things["things"][-1]["thingName"].should.equal("150")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/150"
    )

    things = client.list_things(nextToken=things["nextToken"])
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("151")
    things["things"][0]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/151"
    )
    things["things"][-1]["thingName"].should.equal("200")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/200"
    )


@mock_iot
def test_list_things_with_attribute_and_thing_type_filter_and_next_token():
    client = boto3.client("iot", region_name="ap-northeast-1")
    client.create_thing_type(thingTypeName="my-thing-type")

    for i in range(0, 200):
        if not (i + 1) % 3:
            attribute_payload = {"attributes": {"foo": "bar"}}
        elif not (i + 1) % 5:
            attribute_payload = {"attributes": {"bar": "foo"}}
        else:
            attribute_payload = {}

        if not (i + 1) % 2:
            thing_type_name = "my-thing-type"
            client.create_thing(
                thingName=str(i + 1),
                thingTypeName=thing_type_name,
                attributePayload=attribute_payload,
            )
        else:
            client.create_thing(
                thingName=str(i + 1), attributePayload=attribute_payload
            )

    # Test filter for thingTypeName
    things = client.list_things(thingTypeName=thing_type_name)
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("2")
    things["things"][0]["thingArn"].should.equal("arn:aws:iot:ap-northeast-1:1:thing/2")
    things["things"][-1]["thingName"].should.equal("100")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/100"
    )
    all(item["thingTypeName"] == thing_type_name for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], thingTypeName=thing_type_name
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("102")
    things["things"][0]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/102"
    )
    things["things"][-1]["thingName"].should.equal("200")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/200"
    )
    all(item["thingTypeName"] == thing_type_name for item in things["things"])

    # Test filter for attributes
    things = client.list_things(attributeName="foo", attributeValue="bar")
    things.should.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(50)
    things["things"][0]["thingName"].should.equal("3")
    things["things"][0]["thingArn"].should.equal("arn:aws:iot:ap-northeast-1:1:thing/3")
    things["things"][-1]["thingName"].should.equal("150")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/150"
    )
    all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    things = client.list_things(
        nextToken=things["nextToken"], attributeName="foo", attributeValue="bar"
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(16)
    things["things"][0]["thingName"].should.equal("153")
    things["things"][0]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/153"
    )
    things["things"][-1]["thingName"].should.equal("198")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/198"
    )
    all(item["attributes"] == {"foo": "bar"} for item in things["things"])

    # Test filter for attributes and thingTypeName
    things = client.list_things(
        thingTypeName=thing_type_name, attributeName="foo", attributeValue="bar"
    )
    things.should_not.have.key("nextToken")
    things.should.have.key("things").which.should.have.length_of(33)
    things["things"][0]["thingName"].should.equal("6")
    things["things"][0]["thingArn"].should.equal("arn:aws:iot:ap-northeast-1:1:thing/6")
    things["things"][-1]["thingName"].should.equal("198")
    things["things"][-1]["thingArn"].should.equal(
        "arn:aws:iot:ap-northeast-1:1:thing/198"
    )
    all(
        item["attributes"] == {"foo": "bar"}
        and item["thingTypeName"] == thing_type_name
        for item in things["things"]
    )


@mock_iot
def test_endpoints():
    region_name = "ap-northeast-1"
    client = boto3.client("iot", region_name=region_name)

    # iot:Data
    endpoint = client.describe_endpoint(endpointType="iot:Data")
    endpoint.should.have.key("endpointAddress").which.should_not.contain("ats")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        "iot.{}.amazonaws.com".format(region_name)
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Data-ATS")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        "ats.iot.{}.amazonaws.com".format(region_name)
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:CredentialProvider")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        "credentials.iot.{}.amazonaws.com".format(region_name)
    )

    # iot:Data-ATS
    endpoint = client.describe_endpoint(endpointType="iot:Jobs")
    endpoint.should.have.key("endpointAddress").which.should.contain(
        "jobs.iot.{}.amazonaws.com".format(region_name)
    )

    # raise InvalidRequestException
    try:
        client.describe_endpoint(endpointType="iot:Abc")
    except client.exceptions.InvalidRequestException as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("InvalidRequestException")
    else:
        raise Exception("Should have raised error")


@mock_iot
def test_certificate_id_generation_deterministic():
    # Creating the same certificate twice should result in the same certificate ID
    client = boto3.client("iot", region_name="us-east-1")
    cert1 = client.create_keys_and_certificate(setAsActive=False)
    client.delete_certificate(certificateId=cert1["certificateId"])

    cert2 = client.register_certificate(
        certificatePem=cert1["certificatePem"], setAsActive=False
    )
    cert2.should.have.key("certificateId").which.should.equal(cert1["certificateId"])
    client.delete_certificate(certificateId=cert2["certificateId"])


@mock_iot
def test_certs():
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificatePem").which.should_not.be.none
    cert.should.have.key("keyPair")
    cert["keyPair"].should.have.key("PublicKey").which.should_not.be.none
    cert["keyPair"].should.have.key("PrivateKey").which.should_not.be.none
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("certificateArn").which.should_not.be.none
    cert_desc.should.have.key("certificateId").which.should_not.be.none
    cert_desc.should.have.key("certificatePem").which.should_not.be.none
    cert_desc.should.have.key("validity").which.should_not.be.none
    validity = cert_desc["validity"]
    validity.should.have.key("notBefore").which.should_not.be.none
    validity.should.have.key("notAfter").which.should_not.be.none
    cert_desc.should.have.key("status").which.should.equal("ACTIVE")
    cert_pem = cert_desc["certificatePem"]

    res = client.list_certificates()
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("REVOKED")

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")

    # Test register_certificate flow
    cert = client.register_certificate(certificatePem=cert_pem, setAsActive=True)
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    cert = client.describe_certificate(certificateId=cert_id)
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("REVOKED")

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")

    # Test register_certificate without CA flow
    cert = client.register_certificate_without_ca(
        certificatePem=cert_pem, status="INACTIVE"
    )
    cert.should.have.key("certificateId").which.should_not.be.none
    cert.should.have.key("certificateArn").which.should_not.be.none
    cert_id = cert["certificateId"]

    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)
    for cert in res["certificates"]:
        cert.should.have.key("certificateArn").which.should_not.be.none
        cert.should.have.key("certificateId").which.should_not.be.none
        cert.should.have.key("status").which.should_not.be.none
        cert.should.have.key("creationDate").which.should_not.be.none

    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates")


@mock_iot
def test_create_certificate_validation():
    # Test we can't create a cert that already exists
    client = boto3.client("iot", region_name="us-east-1")
    cert = client.create_keys_and_certificate(setAsActive=False)

    with pytest.raises(ClientError) as e:
        client.register_certificate(
            certificatePem=cert["certificatePem"], setAsActive=False
        )
    e.value.response["Error"]["Message"].should.contain(
        "The certificate is already provisioned or registered"
    )

    with pytest.raises(ClientError) as e:
        client.register_certificate_without_ca(
            certificatePem=cert["certificatePem"], status="ACTIVE"
        )
    e.value.response["Error"]["Message"].should.contain(
        "The certificate is already provisioned or registered"
    )


@mock_iot
def test_delete_policy_validation():
    doc = """{
    "Version": "2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "iot: *"
            ],
            "Resource":"*"
        }
      ]
    }
    """
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    policy_name = "my-policy"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    with pytest.raises(ClientError) as e:
        client.delete_policy(policyName=policy_name)
    e.value.response["Error"]["Message"].should.contain(
        "The policy cannot be deleted as the policy is attached to one or more principals (name=%s)"
        % policy_name
    )
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_policy(policyName=policy_name)
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)


@mock_iot
def test_delete_certificate_validation():
    doc = """{
    "Version": "2012-10-17",
    "Statement":[
        {
            "Effect":"Allow",
            "Action":[
                "iot: *"
            ],
            "Resource":"*"
        }
      ]
    }
    """
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_id = cert["certificateId"]
    cert_arn = cert["certificateArn"]
    policy_name = "my-policy"
    thing_name = "thing-1"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.create_thing(thingName=thing_name)
    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.value.response["Error"]["Message"].should.contain(
        "Certificate must be deactivated (not ACTIVE) before deletion."
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.update_certificate(certificateId=cert_id, newStatus="REVOKED")
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.value.response["Error"]["Message"].should.contain(
        "Things must be detached before deletion (arn: %s)" % cert_arn
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    with pytest.raises(ClientError) as e:
        client.delete_certificate(certificateId=cert_id)
    e.value.response["Error"]["Message"].should.contain(
        "Certificate policies must be detached before deletion (arn: %s)" % cert_arn
    )
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(1)

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    client.delete_certificate(certificateId=cert_id)
    res = client.list_certificates()
    res.should.have.key("certificates").which.should.have.length_of(0)


@mock_iot
def test_certs_create_inactive():
    client = boto3.client("iot", region_name="ap-northeast-1")
    cert = client.create_keys_and_certificate(setAsActive=False)
    cert_id = cert["certificateId"]

    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("INACTIVE")

    client.update_certificate(certificateId=cert_id, newStatus="ACTIVE")
    cert = client.describe_certificate(certificateId=cert_id)
    cert.should.have.key("certificateDescription")
    cert_desc = cert["certificateDescription"]
    cert_desc.should.have.key("status").which.should.equal("ACTIVE")


@mock_iot
def test_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-policy"
    doc = "{}"
    policy = client.create_policy(policyName=name, policyDocument=doc)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("policyVersionId").which.should.equal("1")

    policy = client.get_policy(policyName=name)
    policy.should.have.key("policyName").which.should.equal(name)
    policy.should.have.key("policyArn").which.should_not.be.none
    policy.should.have.key("policyDocument").which.should.equal(doc)
    policy.should.have.key("defaultVersionId").which.should.equal("1")

    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    client.delete_policy(policyName=name)
    res = client.list_policies()
    res.should.have.key("policies").which.should.have.length_of(0)


@mock_iot
def test_principal_policy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"
    client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    # do nothing if policy have already attached to certificate
    client.attach_policy(policyName=policy_name, target=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(1)
    for principal in res["principals"]:
        principal.should_not.be.none

    client.detach_policy(policyName=policy_name, target=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(0)
    with pytest.raises(ClientError) as e:
        client.detach_policy(policyName=policy_name, target=cert_arn)
    e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")


@mock_iot
def test_principal_policy_deprecated():
    client = boto3.client("iot", region_name="ap-northeast-1")
    policy_name = "my-policy"
    doc = "{}"
    policy = client.create_policy(policyName=policy_name, policyDocument=doc)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_principal_policy(policyName=policy_name, principal=cert_arn)

    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(1)
    for policy in res["policies"]:
        policy.should.have.key("policyName").which.should_not.be.none
        policy.should.have.key("policyArn").which.should_not.be.none

    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(1)
    for principal in res["principals"]:
        principal.should_not.be.none

    client.detach_principal_policy(policyName=policy_name, principal=cert_arn)
    res = client.list_principal_policies(principal=cert_arn)
    res.should.have.key("policies").which.should.have.length_of(0)
    res = client.list_policy_principals(policyName=policy_name)
    res.should.have.key("principals").which.should.have.length_of(0)


@mock_iot
def test_principal_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing"
    thing = client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key("things").which.should.have.length_of(1)
    res["things"][0].should.equal(thing_name)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key("principals").which.should.have.length_of(1)
    for principal in res["principals"]:
        principal.should_not.be.none

    client.detach_thing_principal(thingName=thing_name, principal=cert_arn)
    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key("things").which.should.have.length_of(0)
    res = client.list_thing_principals(thingName=thing_name)
    res.should.have.key("principals").which.should.have.length_of(0)

    with pytest.raises(ClientError) as e:
        client.list_thing_principals(thingName="xxx")

    e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")
    e.value.response["Error"]["Message"].should.equal(
        "Failed to list principals for thing xxx because the thing does not exist in your account"
    )


@mock_iot
def test_delete_principal_thing():
    client = boto3.client("iot", region_name="ap-northeast-1")
    thing_name = "my-thing"
    thing = client.create_thing(thingName=thing_name)
    cert = client.create_keys_and_certificate(setAsActive=True)
    cert_arn = cert["certificateArn"]
    cert_id = cert["certificateId"]

    client.attach_thing_principal(thingName=thing_name, principal=cert_arn)

    client.delete_thing(thingName=thing_name)
    res = client.list_principal_things(principal=cert_arn)
    res.should.have.key("things").which.should.have.length_of(0)

    client.update_certificate(certificateId=cert_id, newStatus="INACTIVE")
    client.delete_certificate(certificateId=cert_id)


class TestListThingGroup:
    group_name_1a = "my-group-name-1a"
    group_name_1b = "my-group-name-1b"
    group_name_2a = "my-group-name-2a"
    group_name_2b = "my-group-name-2b"
    group_name_3a = "my-group-name-3a"
    group_name_3b = "my-group-name-3b"
    group_name_3c = "my-group-name-3c"
    group_name_3d = "my-group-name-3d"
    tree_dict = {
        group_name_1a: {
            group_name_2a: {group_name_3a: {}, group_name_3b: {}},
            group_name_2b: {group_name_3c: {}, group_name_3d: {}},
        },
        group_name_1b: {},
    }

    @mock_iot
    def test_should_list_all_groups(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups()
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(8)

    @mock_iot
    def test_should_list_all_groups_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)

    @mock_iot
    def test_should_list_all_groups_filtered_by_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(6)
        resp = client.list_thing_groups(parentGroup=self.group_name_2a)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(parentGroup=self.group_name_1b)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)
        with pytest.raises(ClientError) as e:
            client.list_thing_groups(parentGroup="inexistant-group-name")
            e.value.response["Error"]["Code"].should.equal("ResourceNotFoundException")

    @mock_iot
    def test_should_list_all_groups_filtered_by_parent_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(parentGroup=self.group_name_1a, recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(parentGroup=self.group_name_2a, recursive=False)
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(namePrefixFilter="my-group-name-1")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(namePrefixFilter="my-group-name-3")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(4)
        resp = client.list_thing_groups(namePrefixFilter="prefix-which-doesn-not-match")
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix_non_recursively(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-1", recursive=False
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", recursive=False
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)

    @mock_iot
    def test_should_list_all_groups_filtered_by_name_prefix_and_parent(self):
        # setup
        client = boto3.client("iot", region_name="ap-northeast-1")
        group_catalog = generate_thing_group_tree(client, self.tree_dict)
        # test
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-2", parentGroup=self.group_name_1a
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(2)
        resp = client.list_thing_groups(
            namePrefixFilter="my-group-name-3", parentGroup=self.group_name_1a
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(4)
        resp = client.list_thing_groups(
            namePrefixFilter="prefix-which-doesn-not-match",
            parentGroup=self.group_name_1a,
        )
        resp.should.have.key("thingGroups")
        resp["thingGroups"].should.have.length_of(0)


@mock_iot
def test_delete_thing_group():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group-name-1a"
    group_name_2a = "my-group-name-2a"
    tree_dict = {
        group_name_1a: {group_name_2a: {},},
    }
    group_catalog = generate_thing_group_tree(client, tree_dict)

    # delete group with child
    try:
        client.delete_thing_group(thingGroupName=group_name_1a)
    except client.exceptions.InvalidRequestException as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("InvalidRequestException")
    else:
        raise Exception("Should have raised error")

    # delete child group
    client.delete_thing_group(thingGroupName=group_name_2a)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(1)
    res["thingGroups"].should_not.have.key(group_name_2a)

    # now that there is no child group, we can delete the previous group safely
    client.delete_thing_group(thingGroupName=group_name_1a)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(0)

    # Deleting an invalid thing group does not raise an error.
    res = client.delete_thing_group(thingGroupName="non-existent-group-name")
    res["ResponseMetadata"]["HTTPStatusCode"].should.equal(200)


@mock_iot
def test_describe_thing_group_metadata_hierarchy():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name_1a = "my-group-name-1a"
    group_name_1b = "my-group-name-1b"
    group_name_2a = "my-group-name-2a"
    group_name_2b = "my-group-name-2b"
    group_name_3a = "my-group-name-3a"
    group_name_3b = "my-group-name-3b"
    group_name_3c = "my-group-name-3c"
    group_name_3d = "my-group-name-3d"

    tree_dict = {
        group_name_1a: {
            group_name_2a: {group_name_3a: {}, group_name_3b: {}},
            group_name_2b: {group_name_3c: {}, group_name_3d: {}},
        },
        group_name_1b: {},
    }
    group_catalog = generate_thing_group_tree(client, tree_dict)

    # describe groups
    # groups level 1
    # 1a
    thing_group_description1a = client.describe_thing_group(
        thingGroupName=group_name_1a
    )
    thing_group_description1a.should.have.key("thingGroupName").which.should.equal(
        group_name_1a
    )
    thing_group_description1a.should.have.key("thingGroupProperties")
    thing_group_description1a.should.have.key("thingGroupMetadata")
    thing_group_description1a["thingGroupMetadata"].should.have.key("creationDate")
    thing_group_description1a.should.have.key("version")
    # 1b
    thing_group_description1b = client.describe_thing_group(
        thingGroupName=group_name_1b
    )
    thing_group_description1b.should.have.key("thingGroupName").which.should.equal(
        group_name_1b
    )
    thing_group_description1b.should.have.key("thingGroupProperties")
    thing_group_description1b.should.have.key("thingGroupMetadata")
    thing_group_description1b["thingGroupMetadata"].should.have.length_of(1)
    thing_group_description1b["thingGroupMetadata"].should.have.key("creationDate")
    thing_group_description1b.should.have.key("version")
    # groups level 2
    # 2a
    thing_group_description2a = client.describe_thing_group(
        thingGroupName=group_name_2a
    )
    thing_group_description2a.should.have.key("thingGroupName").which.should.equal(
        group_name_2a
    )
    thing_group_description2a.should.have.key("thingGroupProperties")
    thing_group_description2a.should.have.key("thingGroupMetadata")
    thing_group_description2a["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description2a["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_1a)
    thing_group_description2a["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description2a["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(1)
    thing_group_description2a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description2a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description2a.should.have.key("version")
    # 2b
    thing_group_description2b = client.describe_thing_group(
        thingGroupName=group_name_2b
    )
    thing_group_description2b.should.have.key("thingGroupName").which.should.equal(
        group_name_2b
    )
    thing_group_description2b.should.have.key("thingGroupProperties")
    thing_group_description2b.should.have.key("thingGroupMetadata")
    thing_group_description2b["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description2b["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_1a)
    thing_group_description2b["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description2b["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(1)
    thing_group_description2b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description2b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description2b.should.have.key("version")
    # groups level 3
    # 3a
    thing_group_description3a = client.describe_thing_group(
        thingGroupName=group_name_3a
    )
    thing_group_description3a.should.have.key("thingGroupName").which.should.equal(
        group_name_3a
    )
    thing_group_description3a.should.have.key("thingGroupProperties")
    thing_group_description3a.should.have.key("thingGroupMetadata")
    thing_group_description3a["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3a["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2a)
    thing_group_description3a["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3a["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2a)
    thing_group_description3a["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2a]["thingGroupArn"])
    thing_group_description3a.should.have.key("version")
    # 3b
    thing_group_description3b = client.describe_thing_group(
        thingGroupName=group_name_3b
    )
    thing_group_description3b.should.have.key("thingGroupName").which.should.equal(
        group_name_3b
    )
    thing_group_description3b.should.have.key("thingGroupProperties")
    thing_group_description3b.should.have.key("thingGroupMetadata")
    thing_group_description3b["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3b["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2a)
    thing_group_description3b["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3b["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2a)
    thing_group_description3b["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2a]["thingGroupArn"])
    thing_group_description3b.should.have.key("version")
    # 3c
    thing_group_description3c = client.describe_thing_group(
        thingGroupName=group_name_3c
    )
    thing_group_description3c.should.have.key("thingGroupName").which.should.equal(
        group_name_3c
    )
    thing_group_description3c.should.have.key("thingGroupProperties")
    thing_group_description3c.should.have.key("thingGroupMetadata")
    thing_group_description3c["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3c["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2b)
    thing_group_description3c["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3c["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2b)
    thing_group_description3c["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2b]["thingGroupArn"])
    thing_group_description3c.should.have.key("version")
    # 3d
    thing_group_description3d = client.describe_thing_group(
        thingGroupName=group_name_3d
    )
    thing_group_description3d.should.have.key("thingGroupName").which.should.equal(
        group_name_3d
    )
    thing_group_description3d.should.have.key("thingGroupProperties")
    thing_group_description3d.should.have.key("thingGroupMetadata")
    thing_group_description3d["thingGroupMetadata"].should.have.length_of(3)
    thing_group_description3d["thingGroupMetadata"].should.have.key(
        "parentGroupName"
    ).being.equal(group_name_2b)
    thing_group_description3d["thingGroupMetadata"].should.have.key(
        "rootToParentThingGroups"
    )
    thing_group_description3d["thingGroupMetadata"][
        "rootToParentThingGroups"
    ].should.have.length_of(2)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupName"
    ].should.match(group_name_1a)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][0][
        "groupArn"
    ].should.match(group_catalog[group_name_1a]["thingGroupArn"])
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupName"
    ].should.match(group_name_2b)
    thing_group_description3d["thingGroupMetadata"]["rootToParentThingGroups"][1][
        "groupArn"
    ].should.match(group_catalog[group_name_2b]["thingGroupArn"])
    thing_group_description3d.should.have.key("version")


@mock_iot
def test_thing_groups():
    client = boto3.client("iot", region_name="ap-northeast-1")
    group_name = "my-group-name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")
    thing_group["thingGroupArn"].should.contain(group_name)

    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(1)
    for thing_group in res["thingGroups"]:
        thing_group.should.have.key("groupName").which.should_not.be.none
        thing_group.should.have.key("groupArn").which.should_not.be.none

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupProperties")
    thing_group.should.have.key("thingGroupMetadata")
    thing_group.should.have.key("version")
    thing_group.should.have.key("thingGroupArn")
    thing_group["thingGroupArn"].should.contain(group_name)

    # delete thing group
    client.delete_thing_group(thingGroupName=group_name)
    res = client.list_thing_groups()
    res.should.have.key("thingGroups").which.should.have.length_of(0)

    # props create test
    props = {
        "thingGroupDescription": "my first thing group",
        "attributePayload": {"attributes": {"key1": "val01", "Key02": "VAL2"}},
    }
    thing_group = client.create_thing_group(
        thingGroupName=group_name, thingGroupProperties=props
    )
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")

    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("key1").which.should.equal("val01")
    res_props.should.have.key("Key02").which.should.equal("VAL2")

    # props update test with merge
    new_props = {"attributePayload": {"attributes": {"k3": "v3"}, "merge": True}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("key1").which.should.equal("val01")
    res_props.should.have.key("Key02").which.should.equal("VAL2")

    res_props.should.have.key("k3").which.should.equal("v3")

    # props update test
    new_props = {"attributePayload": {"attributes": {"k4": "v4"}}}
    client.update_thing_group(thingGroupName=group_name, thingGroupProperties=new_props)
    thing_group = client.describe_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupProperties").which.should.have.key(
        "attributePayload"
    ).which.should.have.key("attributes")
    res_props = thing_group["thingGroupProperties"]["attributePayload"]["attributes"]
    res_props.should.have.key("k4").which.should.equal("v4")
    res_props.should_not.have.key("key1")


@mock_iot
def test_thing_group_relations():
    client = boto3.client("iot", region_name="ap-northeast-1")
    name = "my-thing"
    group_name = "my-group-name"

    # thing group
    thing_group = client.create_thing_group(thingGroupName=group_name)
    thing_group.should.have.key("thingGroupName").which.should.equal(group_name)
    thing_group.should.have.key("thingGroupArn")

    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # add in 4 way
    client.add_thing_to_thing_group(thingGroupName=group_name, thingName=name)
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingArn=thing["thingArn"]
    )
    client.add_thing_to_thing_group(
        thingGroupName=group_name, thingArn=thing["thingArn"]
    )
    client.add_thing_to_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingName=name
    )

    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(1)

    thing_groups = client.list_thing_groups_for_thing(thingName=name)
    thing_groups.should.have.key("thingGroups")
    thing_groups["thingGroups"].should.have.length_of(1)

    # remove in 4 way
    client.remove_thing_from_thing_group(thingGroupName=group_name, thingName=name)
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingArn=thing["thingArn"]
    )
    client.remove_thing_from_thing_group(
        thingGroupName=group_name, thingArn=thing["thingArn"]
    )
    client.remove_thing_from_thing_group(
        thingGroupArn=thing_group["thingGroupArn"], thingName=name
    )
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(0)

    # update thing group for thing
    client.update_thing_groups_for_thing(thingName=name, thingGroupsToAdd=[group_name])
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(1)

    client.update_thing_groups_for_thing(
        thingName=name, thingGroupsToRemove=[group_name]
    )
    things = client.list_things_in_thing_group(thingGroupName=group_name)
    things.should.have.key("things")
    things["things"].should.have.length_of(0)


@mock_iot
def test_create_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing# job document
    #     job_document = {
    #         "field": "value"
    #     }
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")


@mock_iot
def test_list_jobs():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing# job document
    #     job_document = {
    #         "field": "value"
    #     }
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job1 = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job1.should.have.key("jobId").which.should.equal(job_id)
    job1.should.have.key("jobArn")
    job1.should.have.key("description")

    job2 = client.create_job(
        jobId=job_id + "1",
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job2.should.have.key("jobId").which.should.equal(job_id + "1")
    job2.should.have.key("jobArn")
    job2.should.have.key("description")

    jobs = client.list_jobs()
    jobs.should.have.key("jobs")
    jobs.should_not.have.key("nextToken")
    jobs["jobs"][0].should.have.key("jobId").which.should.equal(job_id)
    jobs["jobs"][1].should.have.key("jobId").which.should.equal(job_id + "1")


@mock_iot
def test_describe_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("documentSource")
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobArn")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("targets")
    job.should.have.key("job").which.should.have.key("jobProcessDetails")
    job.should.have.key("job").which.should.have.key("lastUpdatedAt")
    job.should.have.key("job").which.should.have.key("createdAt")
    job.should.have.key("job").which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key("job").which.should.have.key(
        "targetSelection"
    ).which.should.equal("CONTINUOUS")
    job.should.have.key("job").which.should.have.key("presignedUrlConfig")
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("roleArn").which.should.equal(
        "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("expiresInSec").which.should.equal(123)
    job.should.have.key("job").which.should.have.key(
        "jobExecutionsRolloutConfig"
    ).which.should.have.key("maximumPerMinute").which.should.equal(10)


@mock_iot
def test_describe_job_1():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobArn")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("targets")
    job.should.have.key("job").which.should.have.key("jobProcessDetails")
    job.should.have.key("job").which.should.have.key("lastUpdatedAt")
    job.should.have.key("job").which.should.have.key("createdAt")
    job.should.have.key("job").which.should.have.key("jobExecutionsRolloutConfig")
    job.should.have.key("job").which.should.have.key(
        "targetSelection"
    ).which.should.equal("CONTINUOUS")
    job.should.have.key("job").which.should.have.key("presignedUrlConfig")
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("roleArn").which.should.equal(
        "arn:aws:iam::1:role/service-role/iot_job_role"
    )
    job.should.have.key("job").which.should.have.key(
        "presignedUrlConfig"
    ).which.should.have.key("expiresInSec").which.should.equal(123)
    job.should.have.key("job").which.should.have.key(
        "jobExecutionsRolloutConfig"
    ).which.should.have.key("maximumPerMinute").which.should.equal(10)


@mock_iot
def test_delete_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)

    client.delete_job(jobId=job_id)

    client.list_jobs()["jobs"].should.have.length_of(0)


@mock_iot
def test_cancel_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)

    job = client.cancel_job(jobId=job_id, reasonCode="Because", comment="You are")
    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job = client.describe_job(jobId=job_id)
    job.should.have.key("job")
    job.should.have.key("job").which.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("job").which.should.have.key("status").which.should.equal(
        "CANCELED"
    )
    job.should.have.key("job").which.should.have.key(
        "forceCanceled"
    ).which.should.equal(False)
    job.should.have.key("job").which.should.have.key("reasonCode").which.should.equal(
        "Because"
    )
    job.should.have.key("job").which.should.have.key("comment").which.should.equal(
        "You are"
    )


@mock_iot
def test_get_job_document_with_document_source():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        documentSource="https://s3-eu-west-1.amazonaws.com/bucket-name/job_document.json",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job_document = client.get_job_document(jobId=job_id)
    job_document.should.have.key("document").which.should.equal("")


@mock_iot
def test_get_job_document_with_document():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")

    job_document = client.get_job_document(jobId=job_id)
    job_document.should.have.key("document").which.should.equal('{"field": "value"}')


@mock_iot
def test_describe_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("jobId").which.should.equal(job_id)
    job_execution["execution"].should.have.key("status").which.should.equal("QUEUED")
    job_execution["execution"].should.have.key("forceCanceled").which.should.equal(
        False
    )
    job_execution["execution"].should.have.key("statusDetails").which.should.equal(
        {"detailsMap": {}}
    )
    job_execution["execution"].should.have.key("thingArn").which.should.equal(
        thing["thingArn"]
    )
    job_execution["execution"].should.have.key("queuedAt")
    job_execution["execution"].should.have.key("startedAt")
    job_execution["execution"].should.have.key("lastUpdatedAt")
    job_execution["execution"].should.have.key("executionNumber").which.should.equal(
        123
    )
    job_execution["execution"].should.have.key("versionNumber").which.should.equal(123)
    job_execution["execution"].should.have.key(
        "approximateSecondsBeforeTimedOut"
    ).which.should.equal(123)

    job_execution = client.describe_job_execution(
        jobId=job_id, thingName=name, executionNumber=123
    )
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("jobId").which.should.equal(job_id)
    job_execution["execution"].should.have.key("status").which.should.equal("QUEUED")
    job_execution["execution"].should.have.key("forceCanceled").which.should.equal(
        False
    )
    job_execution["execution"].should.have.key("statusDetails").which.should.equal(
        {"detailsMap": {}}
    )
    job_execution["execution"].should.have.key("thingArn").which.should.equal(
        thing["thingArn"]
    )
    job_execution["execution"].should.have.key("queuedAt")
    job_execution["execution"].should.have.key("startedAt")
    job_execution["execution"].should.have.key("lastUpdatedAt")
    job_execution["execution"].should.have.key("executionNumber").which.should.equal(
        123
    )
    job_execution["execution"].should.have.key("versionNumber").which.should.equal(123)
    job_execution["execution"].should.have.key(
        "approximateSecondsBeforeTimedOut"
    ).which.should.equal(123)

    try:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=456)
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")
    else:
        raise Exception("Should have raised error")


@mock_iot
def test_cancel_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    client.cancel_job_execution(jobId=job_id, thingName=name)
    job_execution = client.describe_job_execution(jobId=job_id, thingName=name)
    job_execution.should.have.key("execution")
    job_execution["execution"].should.have.key("status").which.should.equal("CANCELED")


@mock_iot
def test_delete_job_execution():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    client.delete_job_execution(jobId=job_id, thingName=name, executionNumber=123)
    try:
        client.describe_job_execution(jobId=job_id, thingName=name, executionNumber=123)
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")
    else:
        raise Exception("Should have raised error")


@mock_iot
def test_list_job_executions_for_job():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.list_job_executions_for_job(jobId=job_id)
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key(
        "thingArn"
    ).which.should.equal(thing["thingArn"])


@mock_iot
def test_list_job_executions_for_thing():
    client = boto3.client("iot", region_name="eu-west-1")
    name = "my-thing"
    job_id = "TestJob"
    # thing
    thing = client.create_thing(thingName=name)
    thing.should.have.key("thingName").which.should.equal(name)
    thing.should.have.key("thingArn")

    # job document
    job_document = {"field": "value"}

    job = client.create_job(
        jobId=job_id,
        targets=[thing["thingArn"]],
        document=json.dumps(job_document),
        description="Description",
        presignedUrlConfig={
            "roleArn": "arn:aws:iam::1:role/service-role/iot_job_role",
            "expiresInSec": 123,
        },
        targetSelection="CONTINUOUS",
        jobExecutionsRolloutConfig={"maximumPerMinute": 10},
    )

    job.should.have.key("jobId").which.should.equal(job_id)
    job.should.have.key("jobArn")
    job.should.have.key("description")

    job_execution = client.list_job_executions_for_thing(thingName=name)
    job_execution.should.have.key("executionSummaries")
    job_execution["executionSummaries"][0].should.have.key("jobId").which.should.equal(
        job_id
    )


class TestTopicRules:
    name = "my-rule"
    payload = {
        "sql": "SELECT * FROM 'topic/*' WHERE something > 0",
        "actions": [
            {"dynamoDBv2": {"putItem": {"tableName": "my-table"}, "roleArn": "my-role"}}
        ],
        "errorAction": {
            "republish": {"qos": 0, "roleArn": "my-role", "topic": "other-topic"}
        },
        "description": "my-description",
        "ruleDisabled": False,
        "awsIotSqlVersion": "2016-03-23",
    }

    @mock_iot
    def test_topic_rule_create(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)

        # duplicated rule name
        with pytest.raises(ClientError) as ex:
            client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceAlreadyExistsException")

    @mock_iot
    def test_topic_rule_list(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # empty response
        res = client.list_topic_rules()
        res.should.have.key("rules").which.should.have.length_of(0)

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)
        client.create_topic_rule(ruleName="my-rule-2", topicRulePayload=self.payload)

        res = client.list_topic_rules()
        res.should.have.key("rules").which.should.have.length_of(2)
        for rule, name in zip(res["rules"], [self.name, "my-rule-2"]):
            rule.should.have.key("ruleName").which.should.equal(name)
            rule.should.have.key("createdAt").which.should_not.be.none
            rule.should.have.key("ruleArn").which.should_not.be.none
            rule.should.have.key("ruleDisabled").which.should.equal(
                self.payload["ruleDisabled"]
            )
            rule.should.have.key("topicPattern").which.should.equal("topic/*")

    @mock_iot
    def test_topic_rule_get(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # no such rule
        with pytest.raises(ClientError) as ex:
            client.get_topic_rule(ruleName=self.name)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)

        rule = client.get_topic_rule(ruleName=self.name)

        rule.should.have.key("ruleArn").which.should_not.be.none
        rule.should.have.key("rule")
        rrule = rule["rule"]
        rrule.should.have.key("actions").which.should.equal(self.payload["actions"])
        rrule.should.have.key("awsIotSqlVersion").which.should.equal(
            self.payload["awsIotSqlVersion"]
        )
        rrule.should.have.key("createdAt").which.should_not.be.none
        rrule.should.have.key("description").which.should.equal(
            self.payload["description"]
        )
        rrule.should.have.key("errorAction").which.should.equal(
            self.payload["errorAction"]
        )
        rrule.should.have.key("ruleDisabled").which.should.equal(
            self.payload["ruleDisabled"]
        )
        rrule.should.have.key("ruleName").which.should.equal(self.name)
        rrule.should.have.key("sql").which.should.equal(self.payload["sql"])

    @mock_iot
    def test_topic_rule_replace(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # no such rule
        with pytest.raises(ClientError) as ex:
            client.replace_topic_rule(ruleName=self.name, topicRulePayload=self.payload)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)

        payload = self.payload.copy()
        payload["description"] = "new-description"
        client.replace_topic_rule(
            ruleName=self.name, topicRulePayload=payload,
        )

        rule = client.get_topic_rule(ruleName=self.name)
        rule["rule"]["ruleName"].should.equal(self.name)
        rule["rule"]["description"].should.equal(payload["description"])

    @mock_iot
    def test_topic_rule_disable(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # no such rule
        with pytest.raises(ClientError) as ex:
            client.disable_topic_rule(ruleName=self.name)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)

        client.disable_topic_rule(ruleName=self.name)

        rule = client.get_topic_rule(ruleName=self.name)
        rule["rule"]["ruleName"].should.equal(self.name)
        rule["rule"]["ruleDisabled"].should.equal(True)

    @mock_iot
    def test_topic_rule_enable(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # no such rule
        with pytest.raises(ClientError) as ex:
            client.enable_topic_rule(ruleName=self.name)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")

        payload = self.payload.copy()
        payload["ruleDisabled"] = True
        client.create_topic_rule(ruleName=self.name, topicRulePayload=payload)

        client.enable_topic_rule(ruleName=self.name)

        rule = client.get_topic_rule(ruleName=self.name)
        rule["rule"]["ruleName"].should.equal(self.name)
        rule["rule"]["ruleDisabled"].should.equal(False)

    @mock_iot
    def test_topic_rule_delete(self):
        client = boto3.client("iot", region_name="ap-northeast-1")

        # no such rule
        with pytest.raises(ClientError) as ex:
            client.delete_topic_rule(ruleName=self.name)
        error_code = ex.value.response["Error"]["Code"]
        error_code.should.equal("ResourceNotFoundException")

        client.create_topic_rule(ruleName=self.name, topicRulePayload=self.payload)

        client.enable_topic_rule(ruleName=self.name)

        client.delete_topic_rule(ruleName=self.name)

        res = client.list_topic_rules()
        res.should.have.key("rules").which.should.have.length_of(0)

    @mock_iot
    def test_deprecate_undeprecate_thing_type(self):
        client = boto3.client("iot", region_name="ap-northeast-1")
        thing_type_name = "my-type-name"
        client.create_thing_type(
            thingTypeName=thing_type_name,
            thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
        )

        res = client.describe_thing_type(thingTypeName=thing_type_name)
        res["thingTypeMetadata"]["deprecated"].should.equal(False)
        client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=False)

        res = client.describe_thing_type(thingTypeName=thing_type_name)
        res["thingTypeMetadata"]["deprecated"].should.equal(True)

        client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=True)

        res = client.describe_thing_type(thingTypeName=thing_type_name)
        res["thingTypeMetadata"]["deprecated"].should.equal(False)

    @mock_iot
    def test_deprecate_thing_type_not_exist(self):
        client = boto3.client("iot", region_name="ap-northeast-1")
        thing_type_name = "my-type-name"
        with pytest.raises(client.exceptions.ResourceNotFoundException):
            client.deprecate_thing_type(
                thingTypeName=thing_type_name, undoDeprecate=False
            )

    @mock_iot
    def test_create_thing_with_deprecated_type(self):
        client = boto3.client("iot", region_name="ap-northeast-1")
        thing_type_name = "my-type-name"
        client.create_thing_type(
            thingTypeName=thing_type_name,
            thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
        )
        client.deprecate_thing_type(thingTypeName=thing_type_name, undoDeprecate=False)
        with pytest.raises(client.exceptions.InvalidRequestException):
            client.create_thing(thingName="thing-name", thingTypeName=thing_type_name)

    @mock_iot
    def test_update_thing_with_deprecated_type(self):
        client = boto3.client("iot", region_name="ap-northeast-1")
        thing_type_name = "my-type-name"
        thing_name = "thing-name"

        client.create_thing_type(
            thingTypeName=thing_type_name,
            thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
        )
        deprecated_thing_type_name = "my-type-name-deprecated"
        client.create_thing_type(
            thingTypeName=deprecated_thing_type_name,
            thingTypeProperties={"searchableAttributes": ["s1", "s2", "s3"]},
        )
        client.deprecate_thing_type(
            thingTypeName=deprecated_thing_type_name, undoDeprecate=False
        )
        client.create_thing(thingName=thing_name, thingTypeName=thing_type_name)
        with pytest.raises(client.exceptions.InvalidRequestException):
            client.update_thing(
                thingName=thing_name, thingTypeName=deprecated_thing_type_name
            )
