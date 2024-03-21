"""Test the different server responses."""

import json
import re
import unittest

import pytest
import xmltodict

import moto.server as server
from moto import mock_aws, settings


@pytest.fixture(scope="function", autouse=True)
def skip_in_server_mode():
    if settings.TEST_SERVER_MODE:
        raise unittest.SkipTest("No point in testing this in ServerMode")


@mock_aws
def test_describe_clusters():
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeClusters")

    result = res.data.decode("utf-8")
    assert "<Clusters></Clusters>" in result


@mock_aws
def test_describe_clusters_with_json_content_type():
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeClusters&ContentType=JSON")

    result = json.loads(res.data.decode("utf-8"))
    del result["DescribeClustersResponse"]["ResponseMetadata"]
    assert result == {
        "DescribeClustersResponse": {"DescribeClustersResult": {"Clusters": []}}
    }


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_create_cluster(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    create_params = (
        "?Action=CreateCluster"
        "&ClusterIdentifier=examplecluster"
        "&MasterUsername=masteruser"
        "&MasterUserPassword=12345678Aa"
        "&NodeType=ds2.xlarge"
    )
    if is_json:
        create_params += "&ContentType=JSON"
    res = test_client.post(create_params)

    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    del result["CreateClusterResponse"]["ResponseMetadata"]
    assert "CreateClusterResponse" in result
    assert "CreateClusterResult" in result["CreateClusterResponse"]
    assert "Cluster" in result["CreateClusterResponse"]["CreateClusterResult"]
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    assert result["MasterUsername"] == "masteruser"
    assert result["MasterUserPassword"] == "****"
    assert result["ClusterVersion"] == "1.0"
    assert result["ClusterSubnetGroupName"] is None
    assert result["AvailabilityZone"] == "us-east-1a"
    assert result["ClusterStatus"] == "creating"
    assert result["NumberOfNodes"] == (1 if is_json else "1")
    assert result["PubliclyAccessible"] is None
    assert result["Encrypted"] is None
    assert result["DBName"] == "dev"
    assert result["NodeType"] == "ds2.xlarge"
    assert result["ClusterIdentifier"] == "examplecluster"
    assert re.match(
        "examplecluster.[a-z0-9]+.us-east-1.redshift.amazonaws.com",
        result["Endpoint"]["Address"],
    )
    assert result["Endpoint"]["Port"] == (5439 if is_json else "5439")
    assert "ClusterCreateTime" in result


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_create_cluster_multiple_params(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    create_params = (
        "?Action=CreateCluster"
        "&ClusterIdentifier=examplecluster"
        "&MasterUsername=masteruser"
        "&MasterUserPassword=12345678Aa"
        "&NumberOfNodes=3"
        "&NodeType=ds2.xlarge"
        "&EnhancedVpcRouting=True"
        "&Tags.Tag.1.Key=key1"
        "&Tags.Tag.1.Value=val1"
        "&Tags.Tag.2.Key=key2"
        "&Tags.Tag.2.Value=val2"
        "&DBName=testdb"
        "&Encrypted=True"
        "&ClusterVersion=2.0"
        "&Port=1234"
    )
    if is_json:
        create_params += "&ContentType=JSON"
    res = test_client.post(create_params)

    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    del result["CreateClusterResponse"]["ResponseMetadata"]
    assert "CreateClusterResponse" in result
    assert "CreateClusterResult" in result["CreateClusterResponse"]
    assert "Cluster" in result["CreateClusterResponse"]["CreateClusterResult"]
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    assert result["MasterUsername"] == "masteruser"
    assert result["MasterUserPassword"] == "****"
    assert result["ClusterVersion"] == "2.0"
    assert result["ClusterSubnetGroupName"] is None
    assert result["AvailabilityZone"] == "us-east-1a"
    assert result["ClusterStatus"] == "creating"
    assert result["NumberOfNodes"] == (3 if is_json else "3")
    assert result["PubliclyAccessible"] is None
    assert result["Encrypted"] == "True"
    assert result["DBName"] == "testdb"
    assert result["NodeType"] == "ds2.xlarge"
    assert result["ClusterIdentifier"] == "examplecluster"
    assert re.match(
        "examplecluster.[a-z0-9]+.us-east-1.redshift.amazonaws.com",
        result["Endpoint"]["Address"],
    )
    assert result["Endpoint"]["Port"] == (1234 if is_json else "1234")
    assert "ClusterCreateTime" in result
    assert "Tags" in result
    tags = result["Tags"]
    if not is_json:
        tags = tags["item"]
    assert tags == [{"Key": "key1", "Value": "val1"}, {"Key": "key2", "Value": "val2"}]


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_create_and_describe_clusters(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()
    cluster_names = ["examplecluster1", "examplecluster2"]

    for name in cluster_names:
        create_params = (
            "?Action=CreateCluster"
            "&ClusterIdentifier=" + name + "&MasterUsername=masteruser"
            "&MasterUserPassword=12345678Aa"
            "&NodeType=ds2.xlarge"
        )
        if is_json:
            create_params += "&ContentType=JSON"
        test_client.post(create_params)

    describe_params = "/?Action=DescribeClusters"
    if is_json:
        describe_params += "&ContentType=JSON"
    res = test_client.get(describe_params)
    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    del result["DescribeClustersResponse"]["ResponseMetadata"]
    assert "DescribeClustersResponse" in result
    assert "DescribeClustersResult" in result["DescribeClustersResponse"]
    assert "Clusters" in result["DescribeClustersResponse"]["DescribeClustersResult"]
    result = result["DescribeClustersResponse"]["DescribeClustersResult"]["Clusters"]
    if not is_json:
        result = result["item"]

    assert len(result) == 2
    for cluster in result:
        assert cluster["ClusterIdentifier"] in cluster_names


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_create_and_describe_cluster_security_group(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()
    security_group_names = ["csg1", "csg2"]

    for csg in security_group_names:
        create_params = (
            "?Action=CreateClusterSecurityGroup"
            "&ClusterSecurityGroupName=" + csg + "&Description=desc for " + csg + ""
        )
        if is_json:
            create_params += "&ContentType=JSON"
        test_client.post(create_params)

    describe_params = "/?Action=DescribeClusterSecurityGroups"
    if is_json:
        describe_params += "&ContentType=JSON"
    res = test_client.get(describe_params)
    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    groups = result["DescribeClusterSecurityGroupsResponse"][
        "DescribeClusterSecurityGroupsResult"
    ]["ClusterSecurityGroups"]
    if not is_json:
        groups = groups["item"]

    descriptions = [g["Description"] for g in groups]
    assert "desc for csg1" in descriptions
    assert "desc for csg2" in descriptions

    # Describe single SG
    describe_params = (
        "/?Action=DescribeClusterSecurityGroups&ClusterSecurityGroupName=csg1"
    )
    if is_json:
        describe_params += "&ContentType=JSON"
    res = test_client.get(describe_params)
    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    groups = result["DescribeClusterSecurityGroupsResponse"][
        "DescribeClusterSecurityGroupsResult"
    ]["ClusterSecurityGroups"]

    if is_json:
        assert len(groups) == 1
        assert groups[0]["ClusterSecurityGroupName"] == "csg1"
    else:
        assert groups["item"]["ClusterSecurityGroupName"] == "csg1"


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_describe_unknown_cluster_security_group(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    describe_params = (
        "/?Action=DescribeClusterSecurityGroups&ClusterSecurityGroupName=unknown"
    )
    if is_json:
        describe_params += "&ContentType=JSON"
    res = test_client.get(describe_params)

    assert res.status_code == 400

    if is_json:
        response = json.loads(res.data.decode("utf-8"))
    else:
        response = xmltodict.parse(res.data.decode("utf-8"), dict_constructor=dict)[
            "RedshiftClientError"
        ]
    error = response["Error"]

    assert error["Code"] == "ClusterSecurityGroupNotFound"
    assert error["Message"] == "Security group unknown not found."


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_aws
def test_create_cluster_with_security_group(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()
    security_group_names = ["csg1", "csg2"]

    for csg in security_group_names:
        create_params = (
            "?Action=CreateClusterSecurityGroup"
            "&ClusterSecurityGroupName=" + csg + "&Description=desc for " + csg + ""
        )
        if is_json:
            create_params += "&ContentType=JSON"
        res = test_client.post(create_params)

        response = res.data.decode("utf-8")

        if is_json:
            response = json.loads(response)
        else:
            response = xmltodict.parse(response, dict_constructor=dict)

        del response["CreateClusterSecurityGroupResponse"]["ResponseMetadata"]
        assert "CreateClusterSecurityGroupResponse" in response
        response = response["CreateClusterSecurityGroupResponse"]
        assert "CreateClusterSecurityGroupResult" in response
        result = response["CreateClusterSecurityGroupResult"]
        assert "ClusterSecurityGroup" in result
        sg = result["ClusterSecurityGroup"]
        assert sg["ClusterSecurityGroupName"] == csg
        assert sg["Description"] == "desc for " + csg
        assert sg["EC2SecurityGroups"] == ([] if is_json else None)

    # Create Cluster with these security groups
    create_params = (
        "?Action=CreateCluster"
        "&ClusterIdentifier=examplecluster"
        "&MasterUsername=masteruser"
        "&MasterUserPassword=12345678Aa"
        "&NodeType=ds2.xlarge"
        "&ClusterSecurityGroups.member.1=csg1"
        "&ClusterSecurityGroups.member.2=csg2"
    )
    if is_json:
        create_params += "&ContentType=JSON"
    res = test_client.post(create_params)

    result = res.data.decode("utf-8")

    if is_json:
        result = json.loads(result)
    else:
        result = xmltodict.parse(result, dict_constructor=dict)

    del result["CreateClusterResponse"]["ResponseMetadata"]
    assert "CreateClusterResponse" in result
    assert "CreateClusterResult" in result["CreateClusterResponse"]
    assert "Cluster" in result["CreateClusterResponse"]["CreateClusterResult"]
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    security_groups = result["ClusterSecurityGroups"]
    if not is_json:
        security_groups = security_groups["item"]

    assert len(security_groups) == 2
    for csg in security_group_names:
        assert {"ClusterSecurityGroupName": csg, "Status": "active"} in security_groups
