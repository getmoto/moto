from __future__ import unicode_literals

import json
import pytest
import sure  # noqa
import xmltodict

import moto.server as server
from moto import mock_redshift

"""
Test the different server responses
"""


@mock_redshift
def test_describe_clusters():
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeClusters")

    result = res.data.decode("utf-8")
    result.should.contain("<Clusters></Clusters>")


@mock_redshift
def test_describe_clusters_with_json_content_type():
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    res = test_client.get("/?Action=DescribeClusters&ContentType=JSON")

    result = json.loads(res.data.decode("utf-8"))
    del result["DescribeClustersResponse"]["ResponseMetadata"]
    result.should.equal(
        {"DescribeClustersResponse": {"DescribeClustersResult": {"Clusters": []}}}
    )


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
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
    result.should.have.key("CreateClusterResponse")
    result["CreateClusterResponse"].should.have.key("CreateClusterResult")
    result["CreateClusterResponse"]["CreateClusterResult"].should.have.key("Cluster")
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    result.should.have.key("MasterUsername").equal("masteruser")
    result.should.have.key("MasterUserPassword").equal("****")
    result.should.have.key("ClusterVersion").equal("1.0")
    result.should.have.key("ClusterSubnetGroupName").equal(None)
    result.should.have.key("AvailabilityZone").equal("us-east-1a")
    result.should.have.key("ClusterStatus").equal("creating")
    result.should.have.key("NumberOfNodes").equal(1 if is_json else "1")
    result.should.have.key("PubliclyAccessible").equal(None)
    result.should.have.key("Encrypted").equal(None)
    result.should.have.key("DBName").equal("dev")
    result.should.have.key("NodeType").equal("ds2.xlarge")
    result.should.have.key("ClusterIdentifier").equal("examplecluster")
    result.should.have.key("Endpoint").should.have.key("Address").match(
        "examplecluster.[a-z0-9]+.us-east-1.redshift.amazonaws.com"
    )
    result.should.have.key("Endpoint").should.have.key("Port").equal(
        5439 if is_json else "5439"
    )
    result.should.have.key("ClusterCreateTime")


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
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
    result.should.have.key("CreateClusterResponse")
    result["CreateClusterResponse"].should.have.key("CreateClusterResult")
    result["CreateClusterResponse"]["CreateClusterResult"].should.have.key("Cluster")
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    result.should.have.key("MasterUsername").equal("masteruser")
    result.should.have.key("MasterUserPassword").equal("****")
    result.should.have.key("ClusterVersion").equal("2.0")
    result.should.have.key("ClusterSubnetGroupName").equal(None)
    result.should.have.key("AvailabilityZone").equal("us-east-1a")
    result.should.have.key("ClusterStatus").equal("creating")
    result.should.have.key("NumberOfNodes").equal(3 if is_json else "3")
    result.should.have.key("PubliclyAccessible").equal(None)
    result.should.have.key("Encrypted").equal("True")
    result.should.have.key("DBName").equal("testdb")
    result.should.have.key("NodeType").equal("ds2.xlarge")
    result.should.have.key("ClusterIdentifier").equal("examplecluster")
    result.should.have.key("Endpoint").should.have.key("Address").match(
        "examplecluster.[a-z0-9]+.us-east-1.redshift.amazonaws.com"
    )
    result.should.have.key("Endpoint").should.have.key("Port").equal(
        1234 if is_json else "1234"
    )
    result.should.have.key("ClusterCreateTime")
    result.should.have.key("Tags")
    tags = result["Tags"]
    if not is_json:
        tags = tags["item"]
    tags.should.equal(
        [{"Key": "key1", "Value": "val1"}, {"Key": "key2", "Value": "val2"}]
    )


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
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
    result.should.have.key("DescribeClustersResponse")
    result["DescribeClustersResponse"].should.have.key("DescribeClustersResult")
    result["DescribeClustersResponse"]["DescribeClustersResult"].should.have.key(
        "Clusters"
    )
    result = result["DescribeClustersResponse"]["DescribeClustersResult"]["Clusters"]
    if not is_json:
        result = result["item"]

    result.should.have.length_of(2)
    for cluster in result:
        cluster_names.should.contain(cluster["ClusterIdentifier"])


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
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
    descriptions.should.contain("desc for csg1")
    descriptions.should.contain("desc for csg2")

    # Describe single SG
    describe_params = (
        "/?Action=DescribeClusterSecurityGroups" "&ClusterSecurityGroupName=csg1"
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
        groups.should.have.length_of(1)
        groups[0]["ClusterSecurityGroupName"].should.equal("csg1")
    else:
        groups["item"]["ClusterSecurityGroupName"].should.equal("csg1")


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
def test_describe_unknown_cluster_security_group(is_json):
    backend = server.create_backend_app("redshift")
    test_client = backend.test_client()

    describe_params = (
        "/?Action=DescribeClusterSecurityGroups" "&ClusterSecurityGroupName=unknown"
    )
    if is_json:
        describe_params += "&ContentType=JSON"
    res = test_client.get(describe_params)

    res.status_code.should.equal(400)

    if is_json:
        response = json.loads(res.data.decode("utf-8"))
    else:
        response = xmltodict.parse(res.data.decode("utf-8"), dict_constructor=dict)[
            "RedshiftClientError"
        ]
    error = response["Error"]

    error["Code"].should.equal("ClusterSecurityGroupNotFound")
    error["Message"].should.equal("Security group unknown not found.")


@pytest.mark.parametrize("is_json", [True, False], ids=["JSON", "XML"])
@mock_redshift
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
        response.should.have.key("CreateClusterSecurityGroupResponse")
        response = response["CreateClusterSecurityGroupResponse"]
        response.should.have.key("CreateClusterSecurityGroupResult")
        result = response["CreateClusterSecurityGroupResult"]
        result.should.have.key("ClusterSecurityGroup")
        sg = result["ClusterSecurityGroup"]
        sg.should.have.key("ClusterSecurityGroupName").being.equal(csg)
        sg.should.have.key("Description").being.equal("desc for " + csg)
        sg.should.have.key("EC2SecurityGroups").being.equal([] if is_json else None)

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
    result.should.have.key("CreateClusterResponse")
    result["CreateClusterResponse"].should.have.key("CreateClusterResult")
    result["CreateClusterResponse"]["CreateClusterResult"].should.have.key("Cluster")
    result = result["CreateClusterResponse"]["CreateClusterResult"]["Cluster"]

    security_groups = result["ClusterSecurityGroups"]
    if not is_json:
        security_groups = security_groups["item"]

    security_groups.should.have.length_of(2)
    for csg in security_group_names:
        security_groups.should.contain(
            {"ClusterSecurityGroupName": csg, "Status": "active"}
        )
