from unittest import SkipTest

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID

# See our Development Tips on writing tests for hints on how to write good tests:
# http://docs.getmoto.org/en/latest/docs/contributing/development_tips/tests.html


@mock_aws
def test_create_user_no_password_required():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        NoPasswordRequired=True,
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password"
    assert "PasswordCount" not in resp["Authentication"]
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_aws
def test_create_user_with_password_too_short():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpass"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert err["Message"] == "Passwords length must be between 16-128 characters."


@mock_aws
def test_create_user_with_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    assert resp["UserId"] == user_id
    assert resp["UserName"] == "User1"
    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["MinimumEngineVersion"] == "6.0"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 1
    assert (
        resp["ARN"] == f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:{user_id}"
    )


@mock_aws
def test_create_user_without_password():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1", UserName="User1", Engine="Redis", AccessString="?"
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Input Authentication type: null is not in the allowed list: [password,no-password-required,iam]"
    )


@mock_aws
def test_create_user_with_iam():
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "iam"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "iam"


@mock_aws
def test_create_user_invalid_authentication_type():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="User1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "invalidtype"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"
    assert (
        err["Message"]
        == "Input Authentication type: invalidtype is not in the allowed list: [password,no-password-required,iam]"
    )


@mock_aws
def test_create_user_with_iam_with_passwords():
    # IAM authentication mode should not come with password fields
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "iam"},
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"] == "Password field is not allowed with authentication type: iam"
    )


@mock_aws
def test_create_user_authmode_password_with_multiple_password_fields():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="on ~* +@all",
            AuthenticationMode={"Type": "password", "Passwords": ["authmodepassword"]},
            Passwords=["requestpassword"],
            NoPasswordRequired=False,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "Passwords provided via multiple arguments. Use only one argument"
    )


@mock_aws
def test_create_user_with_authmode_password_without_passwords():
    client = boto3.client("elasticache", region_name="us-east-1")
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId="user1",
            UserName="user1",
            Engine="Redis",
            AccessString="?",
            AuthenticationMode={"Type": "password"},
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterCombination"
    assert (
        err["Message"]
        == "A user with Authentication Mode: password, must have at least one password"
    )


@mock_aws
def test_create_user_with_authmode_no_password():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "no-password-required"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password-required"
    assert (
        "PasswordCount" not in resp["Authentication"]
    )  # even though optional, we don't expect it for no-password-required


@mock_aws
def test_create_user_with_no_password_required_and_authmode_nopassword():
    user_id = "user1"
    client = boto3.client("elasticache", region_name="us-east-1")
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        NoPasswordRequired=True,
        AuthenticationMode={"Type": "no-password-required"},
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "no-password"
    assert (
        "PasswordCount" not in resp["Authentication"]
    )  # even though optional, we don't expect it for no-password-required


@mock_aws
def test_create_user_with_no_password_required_and_authmode_different():
    for auth_mode in ["password", "iam"]:
        client = boto3.client("elasticache", region_name="ap-southeast-1")
        with pytest.raises(ClientError) as exc:
            client.create_user(
                UserId="user1",
                UserName="user1",
                Engine="Redis",
                AccessString="on ~* +@all",
                NoPasswordRequired=True,
                AuthenticationMode={"Type": auth_mode},
            )
        err = exc.value.response["Error"]
        assert err["Code"] == "InvalidParameterCombination"
        assert (
            err["Message"]
            == f"No password required flag is true but provided authentication type is {auth_mode}"
        )


@mock_aws
def test_create_user_with_authmode_password():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={
            "Type": "password",
            "Passwords": ["mysecretpassthatsverylong"],
        },
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 1


@mock_aws
def test_create_user_with_authmode_password_multiple():
    # AuthenticationMode should be either 'password' or 'iam' or 'no-password'
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={
            "Type": "password",
            "Passwords": ["mysecretpassthatsverylong", "mysecretpassthatsverylong2"],
        },
    )

    assert resp["Status"] == "active"
    assert resp["Engine"] == "redis"
    assert resp["AccessString"] == "on ~* +@all"
    assert resp["UserGroupIds"] == []
    assert resp["Authentication"]["Type"] == "password"
    assert resp["Authentication"]["PasswordCount"] == 2


@mock_aws
def test_create_user_twice():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="Redis",
            AccessString="on ~* +@all",
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "UserAlreadyExists"
    assert err["Message"] == "User user1 already exists."


@mock_aws
@pytest.mark.parametrize("engine", ["redis", "Redis", "reDis"])
def test_create_user_engine_parameter_is_case_insensitive(engine):
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    resp = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine=engine,
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "iam"},
    )
    assert resp["Engine"] == engine.lower()


@mock_aws
def test_create_user_with_invalid_engine_type():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    user_id = "user1"
    with pytest.raises(ClientError) as exc:
        client.create_user(
            UserId=user_id,
            UserName="User1",
            Engine="invalidengine",
            AccessString="on ~* +@all",
            Passwords=["mysecretpassthatsverylong"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidParameterValue"


@mock_aws
def test_create_user_with_tags():
    # In this test, we will invoke CreateUser with tags
    # and verify the tags are set correctly via ListTagsForResource.
    client = boto3.client("elasticache", region_name="us-east-1")
    user_id = "user1"
    create_user_response = client.create_user(
        UserId=user_id,
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        AuthenticationMode={"Type": "iam"},
        Tags=[{"Key": "TestKey", "Value": "TestValue"}],
    )

    resp = client.list_tags_for_resource(ResourceName=create_user_response["ARN"])
    assert resp["TagList"] == [{"Key": "TestKey", "Value": "TestValue"}]


@mock_aws
def test_delete_user_unknown():
    client = boto3.client("elasticache", region_name="ap-southeast-1")
    with pytest.raises(ClientError) as exc:
        client.delete_user(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."


@mock_aws
def test_delete_user():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    client.delete_user(UserId="user1")

    # Initial status is 'deleting'
    resp = client.describe_users(UserId="user1")
    assert resp["Users"][0]["Status"] == "deleting"

    # User is only deleted after some time
    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    assert exc.value.response["Error"]["Code"] == "UserNotFound"


@mock_aws
def test_describe_users_initial():
    client = boto3.client("elasticache", region_name="us-east-2")
    resp = client.describe_users()

    assert len(resp["Users"]) == 1
    assert resp["Users"][0] == {
        "UserId": "default",
        "UserName": "default",
        "Status": "active",
        "Engine": "redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "no-password"},
        "ARN": f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:user:default",
    }


@mock_aws
def test_describe_users():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    client.create_user(
        UserId="user1",
        UserName="User1",
        Engine="Redis",
        AccessString="on ~* +@all",
        Passwords=["mysecretpassthatsverylong"],
    )

    resp = client.describe_users()

    assert len(resp["Users"]) == 2
    assert {
        "UserId": "user1",
        "UserName": "User1",
        "Status": "active",
        "Engine": "redis",
        "MinimumEngineVersion": "6.0",
        "AccessString": "on ~* +@all",
        "UserGroupIds": [],
        "Authentication": {"Type": "password", "PasswordCount": 1},
        "ARN": f"arn:aws:elasticache:ap-southeast-1:{ACCOUNT_ID}:user:user1",
    } in resp["Users"]


@mock_aws
def test_describe_users_unknown_userid():
    client = boto3.client("elasticache", region_name="ap-southeast-1")

    with pytest.raises(ClientError) as exc:
        client.describe_users(UserId="unknown")
    err = exc.value.response["Error"]
    assert err["Code"] == "UserNotFound"
    assert err["Message"] == "User unknown not found."


@mock_aws
def test_create_redis_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_redis_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "redis"
    cache_cluster_num_cache_nodes = 5

    resp = client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
        AutoMinorVersionUpgrade=True,
        TransitEncryptionEnabled=True,
    )
    cache_cluster = resp["CacheCluster"]

    if cache_cluster["CacheClusterId"] == cache_cluster_id:
        if cache_cluster["Engine"] == cache_cluster_engine:
            if cache_cluster["NumCacheNodes"] == 1:
                test_redis_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["CacheCluster"]["AutoMinorVersionUpgrade"] is True
    assert resp["CacheCluster"]["TransitEncryptionEnabled"] is True
    assert test_redis_cache_cluster_exist


@mock_aws
def test_create_memcached_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_memcached_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    resp = client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )
    cache_cluster = resp["CacheCluster"]

    if cache_cluster["CacheClusterId"] == cache_cluster_id:
        if cache_cluster["Engine"] == cache_cluster_engine:
            if cache_cluster["NumCacheNodes"] == 5:
                test_memcached_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_memcached_cache_cluster_exist


@mock_aws
def test_create_duplicate_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.create_cache_cluster(
            CacheClusterId=cache_cluster_id,
            Engine=cache_cluster_engine,
            NumCacheNodes=cache_cluster_num_cache_nodes,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterAlreadyExists"
    assert err["Message"] == f"Cache cluster {cache_cluster_id} already exists."


@mock_aws
def test_describe_all_cache_clusters():
    client = boto3.client("elasticache", region_name="us-east-2")

    num_clusters = 5
    match_number = 0

    for i in range(num_clusters):
        client.create_cache_cluster(
            CacheClusterId=f"test-cache-cluster-{i}",
            Engine="memcached",
            NumCacheNodes=5,
        )

    resp = client.describe_cache_clusters()
    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    cache_clusters = resp["CacheClusters"]

    for i, cache_cluster in enumerate(cache_clusters):
        if cache_cluster["CacheClusterId"] == f"test-cache-cluster-{i}":
            match_number = match_number + 1

    if match_number == (num_clusters):
        assert True
    else:
        assert False


@mock_aws
def test_describe_specific_cache_clusters():
    client = boto3.client("elasticache", region_name="us-east-2")

    test_memcached_cache_cluster_exist = False

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    client.create_cache_cluster(
        CacheClusterId="test-cache-cluster-2",
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    resp = client.describe_cache_clusters(CacheClusterId=cache_cluster_id)

    cache_clusters = resp["CacheClusters"]

    for cache_cluster in cache_clusters:
        if cache_cluster["CacheClusterId"] == cache_cluster_id:
            test_memcached_cache_cluster_exist = True

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert test_memcached_cache_cluster_exist


@mock_aws
def test_describe_unknown_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_id_unknown = "unknown-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.describe_cache_clusters(
            CacheClusterId=cache_cluster_id_unknown,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterNotFound"
    assert err["Message"] == f"Cache cluster {cache_cluster_id_unknown} not found."


@mock_aws
def test_delete_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    client.delete_cache_cluster(CacheClusterId=cache_cluster_id)

    resp = client.describe_cache_clusters(CacheClusterId=cache_cluster_id)

    assert resp["ResponseMetadata"]["HTTPStatusCode"] == 200
    assert resp["CacheClusters"][0]["CacheClusterStatus"] == "deleting"


@mock_aws
def test_delete_unknown_cache_cluster():
    client = boto3.client("elasticache", region_name="us-east-2")

    cache_cluster_id = "test-cache-cluster"
    cache_cluster_id_unknown = "unknown-cache-cluster"
    cache_cluster_engine = "memcached"
    cache_cluster_num_cache_nodes = 5

    client.create_cache_cluster(
        CacheClusterId=cache_cluster_id,
        Engine=cache_cluster_engine,
        NumCacheNodes=cache_cluster_num_cache_nodes,
    )

    with pytest.raises(ClientError) as exc:
        client.delete_cache_cluster(
            CacheClusterId=cache_cluster_id_unknown,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheClusterNotFound"
    assert err["Message"] == f"Cache cluster {cache_cluster_id_unknown} not found."


@mock_aws
def test_list_tags_cache_cluster():
    conn = boto3.client("elasticache", region_name="ap-southeast-1")
    result = conn.list_tags_for_resource(
        ResourceName="arn:aws:elasticache:us-west-2:1234567890:cluster:foo"
    )
    assert result["TagList"] == []
    test_instance = conn.create_cache_cluster(
        CacheClusterId="test-cache-cluster",
        Engine="memcached",
        NumCacheNodes=2,
        Tags=[{"Key": "foo", "Value": "bar"}, {"Key": "foo1", "Value": "bar1"}],
        SecurityGroupIds=["sg-1234"],
    )
    post_create_result = conn.list_tags_for_resource(
        ResourceName=test_instance["CacheCluster"]["ARN"],
    )
    assert post_create_result["TagList"] == [
        {"Value": "bar", "Key": "foo"},
        {"Value": "bar1", "Key": "foo1"},
    ]


@mock_aws
def test_create_cache_subnet_group():
    client = boto3.client("elasticache", region_name="us-east-2")
    resp = client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
        Tags=[
            {"Key": "foo", "Value": "bar"},
            {"Key": "foo1", "Value": "bar1"},
        ],
    )

    assert (
        resp["CacheSubnetGroup"]["ARN"]
        == f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:subnetgroup:test-subnet-group"
    )
    assert resp["CacheSubnetGroup"]["CacheSubnetGroupName"] == "test-subnet-group"
    assert (
        resp["CacheSubnetGroup"]["CacheSubnetGroupDescription"] == "Test subnet group"
    )
    assert len(resp["CacheSubnetGroup"]["Subnets"]) == 2

    assert resp["CacheSubnetGroup"]["Subnets"][0]["SupportedNetworkTypes"] == ["ipv4"]
    assert resp["CacheSubnetGroup"]["Subnets"][1]["SupportedNetworkTypes"] == ["ipv4"]
    assert resp["CacheSubnetGroup"]["SupportedNetworkTypes"] == ["ipv4"]


@mock_aws
def test_create_cache_subnet_group_and_mock_vpc():
    client = boto3.client("elasticache", region_name="us-east-2")

    # Create a subnet group with two subnets
    ec2_client = boto3.client("ec2", region_name="us-east-2")
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc")
    vpc_id = vpc.get("VpcId")
    subnet_1 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24").get(
        "Subnet"
    )
    subnet_2 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24").get(
        "Subnet"
    )

    resp = client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=[subnet_1.get("SubnetId"), subnet_2.get("SubnetId")],
        Tags=[
            {"Key": "foo", "Value": "bar"},
            {"Key": "foo1", "Value": "bar1"},
        ],
    )

    assert (
        resp["CacheSubnetGroup"]["ARN"]
        == f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:subnetgroup:test-subnet-group"
    )
    assert resp["CacheSubnetGroup"]["CacheSubnetGroupName"] == "test-subnet-group"
    assert (
        resp["CacheSubnetGroup"]["CacheSubnetGroupDescription"] == "Test subnet group"
    )
    assert len(resp["CacheSubnetGroup"]["Subnets"]) == 2
    assert resp["CacheSubnetGroup"]["Subnets"][0]["SupportedNetworkTypes"] == ["ipv4"]
    assert resp["CacheSubnetGroup"]["Subnets"][1]["SupportedNetworkTypes"] == ["ipv4"]
    assert resp["CacheSubnetGroup"]["SupportedNetworkTypes"] == ["ipv4"]


@mock_aws
def test_describe_cache_subnet_groups():
    client = boto3.client("elasticache", region_name="us-east-2")
    client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
    )
    resp = client.describe_cache_subnet_groups()
    assert len(resp["CacheSubnetGroups"]) == 1
    assert resp["CacheSubnetGroups"][0]["CacheSubnetGroupName"] == "test-subnet-group"
    assert len(resp["CacheSubnetGroups"][0]["Subnets"]) == 2


@mock_aws
def test_describe_cache_subnet_group_specific():
    client = boto3.client("elasticache", region_name="us-east-2")
    client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
    )
    resp = client.describe_cache_subnet_groups(CacheSubnetGroupName="test-subnet-group")
    assert len(resp["CacheSubnetGroups"]) == 1
    assert resp["CacheSubnetGroups"][0]["CacheSubnetGroupName"] == "test-subnet-group"
    assert len(resp["CacheSubnetGroups"][0]["Subnets"]) == 2
    assert resp["CacheSubnetGroups"][0]["SupportedNetworkTypes"] == ["ipv4"]


@mock_aws
def test_describe_cache_subnet_group_not_found():
    client = boto3.client("elasticache", region_name="us-east-2")
    cache_subnet_group_unknown = "subnet_cluster_id_unknown"

    with pytest.raises(ClientError) as exc:
        client.describe_cache_subnet_groups(
            CacheSubnetGroupName=cache_subnet_group_unknown,
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheSubnetGroupNotFoundFault"
    assert err["Message"] == f"CacheSubnetGroup {cache_subnet_group_unknown} not found."


@mock_aws
def test_subnet_groups_list_tags():
    client = boto3.client("elasticache", region_name="us-east-2")
    client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
        Tags=[
            {"Key": "foo", "Value": "bar"},
            {"Key": "foo1", "Value": "bar1"},
        ],
    )

    resp = client.list_tags_for_resource(
        ResourceName=f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:subnetgroup:test-subnet-group"
    )
    assert len(resp["TagList"]) == 2
    assert resp["TagList"][0]["Key"] == "foo"
    assert resp["TagList"][0]["Value"] == "bar"
    assert resp["TagList"][1]["Key"] == "foo1"
    assert resp["TagList"][1]["Value"] == "bar1"

    client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group-no-tags",
        CacheSubnetGroupDescription="Test subnet group no tags",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
    )

    resp = client.list_tags_for_resource(
        ResourceName=f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:subnetgroup:test-subnet-group-no-tags"
    )
    assert len(resp["TagList"]) == 0


@mock_aws
def test_cache_subnet_group_already_exists():
    client = boto3.client("elasticache", region_name="us-east-2")
    client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
    )

    with pytest.raises(ClientError) as exc:
        client.create_cache_subnet_group(
            CacheSubnetGroupName="test-subnet-group",
            CacheSubnetGroupDescription="Test subnet group",
            SubnetIds=["subnet-0123456789abcdef0", "subnet-abcdef0123456789"],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "CacheSubnetGroupAlreadyExists"
    assert err["Message"] == "CacheSubnetGroup test-subnet-group already exists."


@mock_aws
def test_cache_subnet_group_with_invalid_subnet_ids():
    client = boto3.client("elasticache", region_name="us-east-2")
    ec2_client = boto3.client("ec2", region_name="us-east-2")
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc")
    vpc2 = ec2_client.create_vpc(CidrBlock="10.1.0.0/16").get("Vpc")
    subnet1 = ec2_client.create_subnet(VpcId=vpc["VpcId"], CidrBlock="10.0.0.0/24").get(
        "Subnet"
    )
    subnet2 = ec2_client.create_subnet(
        VpcId=vpc2["VpcId"], CidrBlock="10.1.0.0/24"
    ).get("Subnet")

    with pytest.raises(ClientError) as exc:
        client.create_cache_subnet_group(
            CacheSubnetGroupName="test-subnet-group",
            CacheSubnetGroupDescription="Test subnet group",
            SubnetIds=[subnet1["SubnetId"], subnet2["SubnetId"]],
            Tags=[
                {"Key": "foo", "Value": "bar"},
                {"Key": "foo1", "Value": "bar1"},
            ],
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidSubnet"


@mock_aws
def test_cache_subnet_group_with_ipv4_and_ipv6_subnets():
    client = boto3.client("elasticache", region_name="us-east-2")
    ec2_client = boto3.client("ec2", region_name="us-east-2")

    vpc = ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16", Ipv6CidrBlock="2600:1f16:1cb1:6b00::/56"
    ).get("Vpc")

    vpc_id = vpc.get("VpcId")

    subnet_dual = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.0.0/24").get(
        "Subnet"
    )
    subnet_dual_id = subnet_dual.get("SubnetId")

    ec2_client.associate_subnet_cidr_block(
        SubnetId=subnet_dual_id, Ipv6CidrBlock="2600:1f16:1cb1:6b00::/60"
    )

    subnet_ipv4 = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24").get(
        "Subnet"
    )
    subnet_ipv4_id = subnet_ipv4.get("SubnetId")

    resp = client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=[subnet_dual_id, subnet_ipv4_id],
        Tags=[
            {"Key": "foo", "Value": "bar"},
            {"Key": "foo1", "Value": "bar1"},
        ],
    )

    if resp["CacheSubnetGroup"]["Subnets"][0]["SubnetIdentifier"] == subnet_dual_id:
        assert resp["CacheSubnetGroup"]["Subnets"][0]["SupportedNetworkTypes"] == [
            "ipv4",
            "dual_stack",
        ]
        assert resp["CacheSubnetGroup"]["Subnets"][1]["SupportedNetworkTypes"] == [
            "ipv4"
        ]
    else:
        assert resp["CacheSubnetGroup"]["Subnets"][0]["SupportedNetworkTypes"] == [
            "ipv4"
        ]
        assert resp["CacheSubnetGroup"]["Subnets"][1]["SupportedNetworkTypes"] == [
            "ipv4",
            "dual_stack",
        ]
    assert len(resp["CacheSubnetGroup"]["SupportedNetworkTypes"]) == 2
    assert "ipv4" in resp["CacheSubnetGroup"]["SupportedNetworkTypes"]
    assert "dual_stack" in resp["CacheSubnetGroup"]["SupportedNetworkTypes"]


# The following test will be skipped until the create_subnet moto feature
# adds support for the Ipv6Native parameter.
@mock_aws
def test_cache_subnet_group_with_ipv6_native_subnets():
    raise SkipTest("create_subnet() does not support Ipv6Native-parameter yet")
    client = boto3.client("elasticache", region_name="us-east-2")
    ec2_client = boto3.client("ec2", region_name="us-east-2")

    vpc = ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16", Ipv6CidrBlock="2600:1f16:1cb1:6b00::/56"
    ).get("Vpc")

    vpc_id = vpc.get("VpcId")

    subnet_ipv6_0 = ec2_client.create_subnet(
        VpcId=vpc_id,
        Ipv6CidrBlock="2600:1f16:1cb1:6b00::/60",
        Ipv6Native=True,
    )
    subnet_ipv6_0_id = subnet_ipv6_0.get("SubnetId")

    subnet_ipv6_1 = ec2_client.create_subnet(
        VpcId=vpc_id, Ipv6CidrBlock="2600:1f16:1cb1:6b10::/60", Ipv6Native=True
    )
    subnet_ipv6_1_id = subnet_ipv6_1.get("SubnetId")

    resp = client.create_cache_subnet_group(
        CacheSubnetGroupName="test-subnet-group",
        CacheSubnetGroupDescription="Test subnet group",
        SubnetIds=[subnet_ipv6_0_id, subnet_ipv6_1_id],
    )

    assert resp["CacheSubnetGroup"]["Subnets"][0]["SupportedNetworkTypes"] == ["ipv6"]
    assert resp["CacheSubnetGroup"]["Subnets"][1]["SupportedNetworkTypes"] == ["ipv6"]
    assert resp["CacheSubnetGroup"]["SupportedNetworkTypes"] == ["ipv6"]


@mock_aws
def test_create_replication_group_cluster_disabled():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id = "test-cluster-disabled"

    resp = client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        NumNodeGroups=1,
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        LogDeliveryConfigurations=[
            {
                "LogType": "slow-log",
                "DestinationType": "cloudwatch-logs",
                "DestinationDetails": {
                    "CloudWatchLogsDetails": {"LogGroup": "test-log-group"}
                },
                "LogFormat": "json",
                "Enabled": True,
            }
        ],
    )

    replication_group = resp["ReplicationGroup"]
    cache_node_id = "0001"
    assert replication_group["ReplicationGroupId"] == replication_group_id
    assert replication_group["Description"] == "test replication group"
    assert replication_group["Status"] == "available"
    assert len(replication_group["MemberClusters"]) == 3
    assert replication_group["MemberClusters"] == [
        f"{replication_group_id}-001",
        f"{replication_group_id}-002",
        f"{replication_group_id}-003",
    ]
    assert len(replication_group["NodeGroups"]) == 1
    assert replication_group["NodeGroups"][0]["NodeGroupId"] == cache_node_id
    assert replication_group["NodeGroups"][0]["PrimaryEndpoint"]["Port"] == 6379

    node_group_members = replication_group["NodeGroups"][0]["NodeGroupMembers"]
    assert len(node_group_members) == 3
    assert node_group_members[0]["CacheClusterId"] == f"{replication_group_id}-001"
    assert node_group_members[0]["CacheNodeId"] == cache_node_id
    assert node_group_members[0]["CurrentRole"] == "primary"
    assert node_group_members[1]["CurrentRole"] == "replica"
    assert node_group_members[2]["CurrentRole"] == "replica"

    assert replication_group["AutomaticFailover"] == "enabled"
    assert replication_group["SnapshottingClusterId"] == f"{replication_group_id}-002"
    assert replication_group["MultiAZ"] == "enabled"
    assert replication_group["SnapshotRetentionLimit"] == 1
    assert not replication_group["ClusterEnabled"]
    assert replication_group["CacheNodeType"] == "cache.t4g.micro"
    assert (
        replication_group["ARN"]
        == f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:replicationgroup:{replication_group_id}"
    )
    assert replication_group["NetworkType"] == "ipv4"
    assert replication_group["ClusterMode"] == "disabled"
    assert replication_group["Engine"] == "redis"

    log_config = replication_group["LogDeliveryConfigurations"][0]
    assert log_config["LogType"] == "slow-log"
    assert log_config["DestinationType"] == "cloudwatch-logs"
    assert log_config["DestinationDetails"] == {
        "CloudWatchLogsDetails": {"LogGroup": "test-log-group"}
    }
    assert log_config["LogFormat"] == "json"


@mock_aws
def test_create_replication_group_cluster_enabled():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id = "test-cluster-enabled"

    resp = client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        ReplicasPerNodeGroup=2,
        NumNodeGroups=3,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        ClusterMode="enabled",
        NodeGroupConfiguration=[
            {
                "NodeGroupId": "0001",
                "PrimaryAvailabilityZone": "us-east-2a",
                "ReplicaAvailabilityZones": ["us-east-2b", "us-east-2c"],
                "PrimaryOutpostArn": f"arn:aws:outposts:us-east-2:{ACCOUNT_ID}:outpost/op-1234567890abcdef0",
                "ReplicaOutpostArns": [
                    f"arn:aws:outposts:us-east-2:{ACCOUNT_ID}:outpost/op-1234567890abcdef1",
                    f"arn:aws:outposts:us-east-2:{ACCOUNT_ID}:outpost/op-1234567890abcdef2",
                ],
            },
            {
                "NodeGroupId": "0003",
                "PrimaryAvailabilityZone": "us-east-2b",
                "ReplicaCount": 1,
                "ReplicaAvailabilityZones": ["us-east-2a"],
            },
            {
                "NodeGroupId": "0002",
                "PrimaryAvailabilityZone": "us-east-2c",
                "ReplicaAvailabilityZones": ["us-east-2b", "us-east-2a"],
            },
        ],
    )

    replication_group = resp["ReplicationGroup"]
    assert replication_group["ReplicationGroupId"] == replication_group_id
    assert len(replication_group["MemberClusters"]) == 8
    assert (
        replication_group["NodeGroups"][0]["NodeGroupMembers"][0]["CacheClusterId"]
        == f"{replication_group_id}-0001-001"
    )
    assert (
        replication_group["NodeGroups"][0]["NodeGroupMembers"][0][
            "PreferredAvailabilityZone"
        ]
        == "us-east-2a"
    )
    assert (
        replication_group["NodeGroups"][0]["NodeGroupMembers"][0]["PreferredOutpostArn"]
        == "arn:aws:outposts:us-east-2:123456789012:outpost/op-1234567890abcdef0"
    )
    assert (
        replication_group["NodeGroups"][0]["NodeGroupMembers"][1][
            "PreferredAvailabilityZone"
        ]
        == "us-east-2b"
    )
    assert (
        replication_group["NodeGroups"][0]["NodeGroupMembers"][2][
            "PreferredAvailabilityZone"
        ]
        == "us-east-2c"
    )

    assert len(replication_group["MemberClustersOutpostArns"]) == 3

    if replication_group["ClusterEnabled"]:
        assert True
    else:
        assert False


@mock_aws
def test_create_replication_groups_single_disabled():
    client = boto3.client("elasticache", region_name="us-east-2")
    replication_group_id = "test-single"
    resp = client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        ClusterMode="disabled",
    )

    replication_group = resp["ReplicationGroup"]
    assert replication_group["SnapshottingClusterId"] == f"{replication_group_id}-001"


@mock_aws
def test_create_replication_groups_single_enabled():
    client = boto3.client("elasticache", region_name="us-east-2")
    replication_group_id = "test-single"
    resp = client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        NodeGroupConfiguration=[{"NodeGroupId": "0001", "Slots": "0-5461"}],
        ClusterMode="enabled",
    )

    replication_group = resp["ReplicationGroup"]
    assert (
        replication_group["SnapshottingClusterId"] == f"{replication_group_id}-0001-001"
    )
    assert replication_group["NodeGroups"][0]["Slots"] == "0-5461"


@mock_aws
def test_describe_replication_groups():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id_disabled = "test-cluster-disabled"
    replication_group_id_enabled = "test-cluster-enabled"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id_disabled,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        NumNodeGroups=1,
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
    )

    client.create_replication_group(
        ReplicationGroupId=replication_group_id_enabled,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        ReplicasPerNodeGroup=2,
        NumNodeGroups=3,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        ClusterMode="enabled",
    )

    describe_resp = client.describe_replication_groups()
    assert len(describe_resp["ReplicationGroups"]) == 2


@mock_aws
def test_describe_replication_groups_cluster_disabled():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id = "test-cluster-disabled"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        PreferredCacheClusterAZs=["us-east-2a", "us-east-2b"],
        ClusterMode="disabled",
    )

    describe_resp = client.describe_replication_groups(
        ReplicationGroupId=replication_group_id
    )
    replication_group = describe_resp["ReplicationGroups"][0]
    cache_node_id = "0001"
    assert replication_group["ReplicationGroupId"] == replication_group_id
    assert replication_group["Description"] == "test replication group"
    assert replication_group["Status"] == "available"
    assert len(replication_group["MemberClusters"]) == 3
    assert replication_group["MemberClusters"] == [
        f"{replication_group_id}-001",
        f"{replication_group_id}-002",
        f"{replication_group_id}-003",
    ]
    assert len(replication_group["NodeGroups"]) == 1
    assert replication_group["NodeGroups"][0]["NodeGroupId"] == cache_node_id
    assert replication_group["NodeGroups"][0]["PrimaryEndpoint"]["Port"] == 6379

    node_group_members = replication_group["NodeGroups"][0]["NodeGroupMembers"]
    assert len(node_group_members) == 3
    assert node_group_members[0]["CacheClusterId"] == f"{replication_group_id}-001"
    assert node_group_members[0]["CacheNodeId"] == cache_node_id
    assert node_group_members[0]["PreferredAvailabilityZone"] == "us-east-2a"
    assert node_group_members[0]["CurrentRole"] == "primary"
    assert node_group_members[1]["CurrentRole"] == "replica"
    assert node_group_members[2]["CurrentRole"] == "replica"

    assert replication_group["AutomaticFailover"] == "enabled"
    assert replication_group["SnapshottingClusterId"] == f"{replication_group_id}-002"
    assert replication_group["MultiAZ"] == "enabled"
    assert replication_group["SnapshotRetentionLimit"] == 1
    if not replication_group["ClusterEnabled"]:
        assert True
    else:
        assert False
    assert replication_group["CacheNodeType"] == "cache.t4g.micro"
    assert (
        replication_group["ARN"]
        == f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:replicationgroup:{replication_group_id}"
    )
    assert replication_group["NetworkType"] == "ipv4"
    assert replication_group["ClusterMode"] == "disabled"
    assert replication_group["Engine"] == "redis"


@mock_aws
def test_describe_replication_groups_cluster_enabled():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id = "test-cluster-enabled"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        ReplicasPerNodeGroup=2,
        NumNodeGroups=3,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        ClusterMode="enabled",
        GlobalReplicationGroupId="test-global-replication-group",
        PrimaryClusterId="test-global-replication-group-001",
    )

    describe_resp = client.describe_replication_groups(
        ReplicationGroupId=replication_group_id
    )

    replication_group = describe_resp["ReplicationGroups"][0]
    assert replication_group["ReplicationGroupId"] == replication_group_id
    assert len(replication_group["MemberClusters"]) == 9
    assert replication_group["ClusterEnabled"]
    group_info = replication_group["GlobalReplicationGroupInfo"]
    assert group_info["GlobalReplicationGroupId"] == "test-global-replication-group"
    assert group_info["GlobalReplicationGroupMemberRole"] == "SECONDARY"


@mock_aws
def test_describe_replication_group_not_found():
    client = boto3.client("elasticache", region_name="us-east-2")
    replication_group_id = "test"

    with pytest.raises(ClientError) as exc:
        client.describe_replication_groups(ReplicationGroupId=replication_group_id)

    err = exc.value.response["Error"]
    assert err["Code"] == "ReplicationGroupNotFoundFault"
    assert err["Message"] == f"Replication group {replication_group_id} not found."


@mock_aws
def test_replication_groups_list_tags():
    client = boto3.client("elasticache", region_name="us-east-2")
    replication_group_id = "test-cluster-disabled"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        NumNodeGroups=1,
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
        Tags=[
            {"Key": "foo", "Value": "bar"},
            {"Key": "foo1", "Value": "bar1"},
        ],
    )

    resp = client.list_tags_for_resource(
        ResourceName=f"arn:aws:elasticache:us-east-2:{ACCOUNT_ID}:replicationgroup:{replication_group_id}"
    )
    assert len(resp["TagList"]) == 2
    assert resp["TagList"][0]["Key"] == "foo"
    assert resp["TagList"][0]["Value"] == "bar"
    assert resp["TagList"][1]["Key"] == "foo1"
    assert resp["TagList"][1]["Value"] == "bar1"


@mock_aws
def test_replication_groups_already_exists():
    client = boto3.client("elasticache", region_name="us-east-2")
    replication_group_id = "test"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        NumNodeGroups=1,
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        CacheSubnetGroupName="test-elasticache-subnet-group",
    )
    with pytest.raises(ClientError) as exc:
        client.create_replication_group(
            ReplicationGroupId=replication_group_id,
            ReplicationGroupDescription="test replication group",
            Engine="redis",
            CacheNodeType="cache.t4g.micro",
            NumNodeGroups=1,
            ReplicasPerNodeGroup=2,
            AutomaticFailoverEnabled=True,
            MultiAZEnabled=True,
            CacheSubnetGroupName="test-elasticache-subnet-group",
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "ReplicationGroupAlreadyExists"
    assert err["Message"] == f"Replication group {replication_group_id} already exists."


@mock_aws
def test_list_tags_raises_error_for_invalid_arn():
    client = boto3.client("elasticache", region_name="us-east-2")
    with pytest.raises(ClientError) as exc:
        client.list_tags_for_resource(ResourceName="invalid-arn")
    err = exc.value.response["Error"]
    assert err["Code"] == "InvalidARN"


@mock_aws
def test_delete_replication_group():
    client = boto3.client("elasticache", region_name="us-east-2")

    replication_group_id = "test-cluster-disabled"

    client.create_replication_group(
        ReplicationGroupId=replication_group_id,
        ReplicationGroupDescription="test replication group",
        Engine="redis",
        CacheNodeType="cache.t4g.micro",
        NumNodeGroups=1,
        ReplicasPerNodeGroup=2,
        AutomaticFailoverEnabled=True,
        MultiAZEnabled=True,
        PrimaryClusterId=f"{replication_group_id}-001",
        CacheSubnetGroupName="test-elasticache-subnet-group",
        SnapshotRetentionLimit=1,
        SnapshotWindow="06:00-07:00",
    )

    delete_resp = client.delete_replication_group(
        ReplicationGroupId=replication_group_id,
        RetainPrimaryCluster=False,
    )
    replication_group = delete_resp["ReplicationGroup"]
    assert replication_group["Status"] == "deleting"
    assert replication_group["ReplicationGroupId"] == replication_group_id
    # Now there are only 2 clusters left, because the primary one is deleted immediately
    assert len(replication_group["MemberClusters"]) == 2
