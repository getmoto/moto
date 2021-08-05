def CREATE_WEB_ACL_BODY(name, scope):
    return {
        "Scope": scope,
        "Name": name,
        "DefaultAction": {"Allow": {}},
        "VisibilityConfig": {
            "SampledRequestsEnabled": False,
            "CloudWatchMetricsEnabled": False,
            "MetricName": "test_metric_name",
        },
    }


def LIST_WEB_ACL_BODY(scope):
    return {"Scope": scope}


def CREATE_ASSOCIATE_WEB_ACL_BODY(web_acl_arn, resource_arn):
    return {
        "WebACLArn": web_acl_arn,
        "ResourceArn": resource_arn,
    }


def CREATE_DISASSOCIATE_WEB_ACL_BODY(resource_arn):
    return {
        "ResourceArn": resource_arn,
    }


def CREATE_GET_WEB_ACL_FOR_RESOURCE_BODY(resource_arn):
    return {
        "ResourceArn": resource_arn,
    }


# Return arn of new alb for testing WAF cmds
def create_alb(elbv2_client, ec2_client):

    security_group = ec2_client.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2_client.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2_client.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2_client.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    response = elbv2_client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
    )

    lb = response.get("LoadBalancers")[0]
    return lb.get("LoadBalancerArn")
