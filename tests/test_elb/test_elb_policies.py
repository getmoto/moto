from uuid import uuid4

import boto3
import pytest
from botocore.exceptions import ClientError

from moto import mock_aws


@mock_aws
def test_create_lb_cookie_stickiness_policy():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["LBCookieStickinessPolicies"]
    assert len(lbc_policies) == 0

    client.create_lb_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieExpirationPeriod=42
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["LBCookieStickinessPolicies"]
    assert len(lbc_policies) == 1
    assert lbc_policies[0] == {"PolicyName": "pname", "CookieExpirationPeriod": 42}


@mock_aws
def test_create_lb_cookie_stickiness_policy_no_expiry():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["LBCookieStickinessPolicies"]
    assert len(lbc_policies) == 0

    client.create_lb_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname"
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["LBCookieStickinessPolicies"]
    assert len(lbc_policies) == 1
    assert lbc_policies[0] == {"PolicyName": "pname"}


@mock_aws
def test_create_app_cookie_stickiness_policy():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    lbc_policies = balancer["Policies"]["AppCookieStickinessPolicies"]
    assert len(lbc_policies) == 0

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    lbc_policies = policies["AppCookieStickinessPolicies"]
    assert len(lbc_policies) == 1
    assert lbc_policies[0] == {"CookieName": "cname", "PolicyName": "pname"}


@mock_aws
def test_create_lb_policy():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="ProxyPolicy",
        PolicyTypeName="ProxyProtocolPolicyType",
        PolicyAttributes=[{"AttributeName": "ProxyProtocol", "AttributeValue": "true"}],
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    policies = balancer["Policies"]
    assert policies["OtherPolicies"] == ["ProxyPolicy"]


@mock_aws
def test_set_policies_of_listener():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "https", "LoadBalancerPort": 81, "InstancePort": 8081},
        ],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    client.set_load_balancer_policies_of_listener(
        LoadBalancerName=lb_name, LoadBalancerPort=81, PolicyNames=["pname"]
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]

    http_l = [
        listener
        for listener in balancer["ListenerDescriptions"]
        if listener["Listener"]["Protocol"] == "HTTP"
    ][0]
    assert http_l["PolicyNames"] == []

    https_l = [
        listener
        for listener in balancer["ListenerDescriptions"]
        if listener["Listener"]["Protocol"] == "HTTPS"
    ][0]
    assert https_l["PolicyNames"] == ["pname"]


@mock_aws
def test_set_policies_of_backend_server():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "https", "LoadBalancerPort": 81, "InstancePort": 8081},
        ],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_app_cookie_stickiness_policy(
        LoadBalancerName=lb_name, PolicyName="pname", CookieName="cname"
    )

    client.set_load_balancer_policies_for_backend_server(
        LoadBalancerName=lb_name, InstancePort=8081, PolicyNames=["pname"]
    )

    balancer = client.describe_load_balancers(LoadBalancerNames=[lb_name])[
        "LoadBalancerDescriptions"
    ][0]
    desc = balancer["BackendServerDescriptions"]
    assert len(desc) == 1
    assert desc[0] == {"InstancePort": 8081, "PolicyNames": ["pname"]}


@mock_aws
def test_describe_load_balancer_policies__initial():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    resp = client.describe_load_balancer_policies(LoadBalancerName=lb_name)
    assert resp["PolicyDescriptions"] == []


@mock_aws
def test_describe_load_balancer_policies():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="ProxyPolicy",
        PolicyTypeName="ProxyProtocolPolicyType",
        PolicyAttributes=[{"AttributeName": "ProxyProtocol", "AttributeValue": "true"}],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="DifferentPolicy",
        PolicyTypeName="DifferentProtocolPolicyType",
        PolicyAttributes=[{"AttributeName": "DiffProtocol", "AttributeValue": "true"}],
    )

    resp = client.describe_load_balancer_policies(LoadBalancerName=lb_name)
    assert len(resp["PolicyDescriptions"]) == 2

    resp = client.describe_load_balancer_policies(
        LoadBalancerName=lb_name, PolicyNames=["DifferentPolicy"]
    )
    assert len(resp["PolicyDescriptions"]) == 1
    assert resp["PolicyDescriptions"][0] == {
        "PolicyName": "DifferentPolicy",
        "PolicyTypeName": "DifferentProtocolPolicyType",
        "PolicyAttributeDescriptions": [
            {"AttributeName": "DiffProtocol", "AttributeValue": "true"}
        ],
    }


@mock_aws
def test_describe_unknown_load_balancer_policy():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    with pytest.raises(ClientError) as exc:
        client.describe_load_balancer_policies(
            LoadBalancerName=lb_name, PolicyNames=["unknown"]
        )
    err = exc.value.response["Error"]
    assert err["Code"] == "PolicyNotFound"


@mock_aws
def test_delete_load_balancer_policies():
    lb_name = str(uuid4())[0:6]

    client = boto3.client("elb", region_name="us-east-1")
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[{"Protocol": "http", "LoadBalancerPort": 80, "InstancePort": 8080}],
        AvailabilityZones=["us-east-1a"],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="ProxyPolicy",
        PolicyTypeName="ProxyProtocolPolicyType",
        PolicyAttributes=[{"AttributeName": "ProxyProtocol", "AttributeValue": "true"}],
    )

    client.create_load_balancer_policy(
        LoadBalancerName=lb_name,
        PolicyName="DifferentPolicy",
        PolicyTypeName="DifferentProtocolPolicyType",
        PolicyAttributes=[{"AttributeName": "DiffProtocol", "AttributeValue": "true"}],
    )

    client.delete_load_balancer_policy(
        LoadBalancerName=lb_name, PolicyName="ProxyPolicy"
    )

    resp = client.describe_load_balancer_policies(LoadBalancerName=lb_name)
    assert len(resp["PolicyDescriptions"]) == 1
