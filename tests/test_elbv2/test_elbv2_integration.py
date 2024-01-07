import boto3

from moto import mock_aws


@mock_aws
def test_modify_listener_using_iam_certificate():
    # Verify we can add a listener for a TargetGroup that is already HTTPS
    client = boto3.client("elbv2", region_name="eu-central-1")
    acm = boto3.client("acm", region_name="eu-central-1")
    ec2 = boto3.resource("ec2", region_name="eu-central-1")
    iam = boto3.client("iam", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="eu-central-1a"
    )

    response = client.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[{"Key": "key_name", "Value": "a_value"}],
    )

    load_balancer_arn = response.get("LoadBalancers")[0].get("LoadBalancerArn")

    response = client.create_target_group(
        Name="a-target", Protocol="HTTPS", Port=8443, VpcId=vpc.id
    )
    target_group = response.get("TargetGroups")[0]
    target_group_arn = target_group["TargetGroupArn"]

    # HTTPS listener
    response = acm.request_certificate(
        DomainName="google.com", SubjectAlternativeNames=["google.com"]
    )
    google_arn = response["CertificateArn"]
    response = client.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol="HTTPS",
        Port=443,
        Certificates=[{"CertificateArn": google_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )
    listener_arn = response["Listeners"][0]["ListenerArn"]

    # Now modify the HTTPS listener with an IAM certificate
    resp = iam.upload_server_certificate(
        ServerCertificateName="certname",
        CertificateBody="certbody",
        PrivateKey="privatekey",
    )
    iam_arn = resp["ServerCertificateMetadata"]["Arn"]

    listener = client.modify_listener(
        ListenerArn=listener_arn,
        Certificates=[{"CertificateArn": iam_arn}],
        DefaultActions=[{"Type": "forward", "TargetGroupArn": target_group_arn}],
    )["Listeners"][0]
    assert listener["Certificates"] == [{"CertificateArn": iam_arn}]
