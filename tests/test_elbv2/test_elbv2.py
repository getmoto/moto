from __future__ import unicode_literals
import boto3
import botocore
from botocore.exceptions import ClientError
from nose.tools import assert_raises
import sure  # noqa

from moto import mock_elbv2, mock_ec2


@mock_elbv2
@mock_ec2
def test_create_load_balancer():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    response = conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    lb = response.get('LoadBalancers')[0]

    lb.get('DNSName').should.equal("my-lb-1.us-east-1.elb.amazonaws.com")
    lb.get('LoadBalancerArn').should.equal('arn:aws:elasticloadbalancing:us-east-1:1:loadbalancer/my-lb/50dc6c495c0c9188')
    lb.get('SecurityGroups').should.equal([security_group.id])
    lb.get('AvailabilityZones').should.equal([
        {'SubnetId': subnet1.id, 'ZoneName': 'us-east-1a'},
        {'SubnetId': subnet2.id, 'ZoneName': 'us-east-1b'}])

    # Ensure the tags persisted
    response = conn.describe_tags(ResourceArns=[lb.get('LoadBalancerArn')])
    tags = {d['Key']: d['Value'] for d in response['TagDescriptions'][0]['Tags']}
    tags.should.equal({'key_name': 'a_value'})


@mock_elbv2
@mock_ec2
def test_describe_load_balancers():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    response = conn.describe_load_balancers()

    response.get('LoadBalancers').should.have.length_of(1)
    lb = response.get('LoadBalancers')[0]
    lb.get('LoadBalancerName').should.equal('my-lb')

    response = conn.describe_load_balancers(LoadBalancerArns=[lb.get('LoadBalancerArn')])
    response.get('LoadBalancers')[0].get('LoadBalancerName').should.equal('my-lb')

    response = conn.describe_load_balancers(Names=['my-lb'])
    response.get('LoadBalancers')[0].get('LoadBalancerName').should.equal('my-lb')

    with assert_raises(ClientError):
        conn.describe_load_balancers(LoadBalancerArns=['not-a/real/arn'])
    with assert_raises(ClientError):
        conn.describe_load_balancers(Names=['nope'])


@mock_elbv2
@mock_ec2
def test_add_remove_tags():
    conn = boto3.client('elbv2', region_name='us-east-1')

    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    lbs = conn.describe_load_balancers()['LoadBalancers']
    lbs.should.have.length_of(1)
    lb = lbs[0]

    with assert_raises(ClientError):
        conn.add_tags(ResourceArns=['missing-arn'],
                      Tags=[{
                          'Key': 'a',
                          'Value': 'b'
                      }])

    conn.add_tags(ResourceArns=[lb.get('LoadBalancerArn')],
                  Tags=[{
                      'Key': 'a',
                      'Value': 'b'
                  }])

    tags = {d['Key']: d['Value'] for d in conn.describe_tags(
        ResourceArns=[lb.get('LoadBalancerArn')])['TagDescriptions'][0]['Tags']}
    tags.should.have.key('a').which.should.equal('b')

    conn.add_tags(ResourceArns=[lb.get('LoadBalancerArn')],
                  Tags=[{
                      'Key': 'a',
                      'Value': 'b'
                  }, {
                      'Key': 'b',
                      'Value': 'b'
                  }, {
                      'Key': 'c',
                      'Value': 'b'
                  }, {
                      'Key': 'd',
                      'Value': 'b'
                  }, {
                      'Key': 'e',
                      'Value': 'b'
                  }, {
                      'Key': 'f',
                      'Value': 'b'
                  }, {
                      'Key': 'g',
                      'Value': 'b'
                  }, {
                      'Key': 'h',
                      'Value': 'b'
                  }, {
                      'Key': 'j',
                      'Value': 'b'
                  }])

    conn.add_tags.when.called_with(ResourceArns=[lb.get('LoadBalancerArn')],
                                   Tags=[{
                                       'Key': 'k',
                                       'Value': 'b'
                                   }]).should.throw(botocore.exceptions.ClientError)

    conn.add_tags(ResourceArns=[lb.get('LoadBalancerArn')],
                  Tags=[{
                      'Key': 'j',
                      'Value': 'c'
                  }])

    tags = {d['Key']: d['Value'] for d in conn.describe_tags(
        ResourceArns=[lb.get('LoadBalancerArn')])['TagDescriptions'][0]['Tags']}

    tags.should.have.key('a').which.should.equal('b')
    tags.should.have.key('b').which.should.equal('b')
    tags.should.have.key('c').which.should.equal('b')
    tags.should.have.key('d').which.should.equal('b')
    tags.should.have.key('e').which.should.equal('b')
    tags.should.have.key('f').which.should.equal('b')
    tags.should.have.key('g').which.should.equal('b')
    tags.should.have.key('h').which.should.equal('b')
    tags.should.have.key('j').which.should.equal('c')
    tags.shouldnt.have.key('k')

    conn.remove_tags(ResourceArns=[lb.get('LoadBalancerArn')],
                     TagKeys=['a'])

    tags = {d['Key']: d['Value'] for d in conn.describe_tags(
        ResourceArns=[lb.get('LoadBalancerArn')])['TagDescriptions'][0]['Tags']}

    tags.shouldnt.have.key('a')
    tags.should.have.key('b').which.should.equal('b')
    tags.should.have.key('c').which.should.equal('b')
    tags.should.have.key('d').which.should.equal('b')
    tags.should.have.key('e').which.should.equal('b')
    tags.should.have.key('f').which.should.equal('b')
    tags.should.have.key('g').which.should.equal('b')
    tags.should.have.key('h').which.should.equal('b')
    tags.should.have.key('j').which.should.equal('c')


@mock_elbv2
@mock_ec2
def test_create_elb_in_multiple_region():
    for region in ['us-west-1', 'us-west-2']:
        conn = boto3.client('elbv2', region_name=region)
        ec2 = boto3.resource('ec2', region_name=region)

        security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
        vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
        subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone=region + 'a')
        subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone=region + 'b')

        conn.create_load_balancer(
            Name='my-lb',
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme='internal',
            Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    list(
        boto3.client('elbv2', region_name='us-west-1').describe_load_balancers().get('LoadBalancers')
    ).should.have.length_of(1)
    list(
        boto3.client('elbv2', region_name='us-west-2').describe_load_balancers().get('LoadBalancers')
    ).should.have.length_of(1)


@mock_elbv2
@mock_ec2
def test_create_target_group_and_listeners():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    response = conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    load_balancer_arn = response.get('LoadBalancers')[0].get('LoadBalancerArn')

    response = conn.create_target_group(
        Name='a-target',
        Protocol='HTTP',
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol='HTTP',
        HealthCheckPort='8080',
        HealthCheckPath='/',
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={'HttpCode': '200'})
    target_group = response.get('TargetGroups')[0]

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get('TargetGroups').should.have.length_of(1)

    # Plain HTTP listener
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[{'Type': 'forward', 'TargetGroupArn': target_group.get('TargetGroupArn')}])
    listener = response.get('Listeners')[0]
    listener.get('Port').should.equal(80)
    listener.get('Protocol').should.equal('HTTP')
    listener.get('DefaultActions').should.equal([{
        'TargetGroupArn': target_group.get('TargetGroupArn'),
        'Type': 'forward'}])
    http_listener_arn = listener.get('ListenerArn')

    # And another with SSL
    response = conn.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol='HTTPS',
        Port=443,
        Certificates=[{'CertificateArn': 'arn:aws:iam:123456789012:server-certificate/test-cert'}],
        DefaultActions=[{'Type': 'forward', 'TargetGroupArn': target_group.get('TargetGroupArn')}])
    listener = response.get('Listeners')[0]
    listener.get('Port').should.equal(443)
    listener.get('Protocol').should.equal('HTTPS')
    listener.get('Certificates').should.equal([{
        'CertificateArn': 'arn:aws:iam:123456789012:server-certificate/test-cert',
    }])
    listener.get('DefaultActions').should.equal([{
        'TargetGroupArn': target_group.get('TargetGroupArn'),
        'Type': 'forward'}])

    https_listener_arn = listener.get('ListenerArn')

    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get('Listeners').should.have.length_of(2)
    response = conn.describe_listeners(ListenerArns=[https_listener_arn])
    response.get('Listeners').should.have.length_of(1)
    listener = response.get('Listeners')[0]
    listener.get('Port').should.equal(443)
    listener.get('Protocol').should.equal('HTTPS')

    response = conn.describe_listeners(ListenerArns=[http_listener_arn, https_listener_arn])
    response.get('Listeners').should.have.length_of(2)

    # Delete one listener
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get('Listeners').should.have.length_of(2)
    conn.delete_listener(ListenerArn=http_listener_arn)
    response = conn.describe_listeners(LoadBalancerArn=load_balancer_arn)
    response.get('Listeners').should.have.length_of(1)

    # Then delete the load balancer
    conn.delete_load_balancer(LoadBalancerArn=load_balancer_arn)

    # It's gone
    response = conn.describe_load_balancers()
    response.get('LoadBalancers').should.have.length_of(0)

    # And it deleted the remaining listener
    response = conn.describe_listeners(ListenerArns=[http_listener_arn, https_listener_arn])
    response.get('Listeners').should.have.length_of(0)

    # But not the target groups
    response = conn.describe_target_groups()
    response.get('TargetGroups').should.have.length_of(1)

    # Which we'll now delete
    conn.delete_target_group(TargetGroupArn=target_group.get('TargetGroupArn'))
    response = conn.describe_target_groups()
    response.get('TargetGroups').should.have.length_of(0)


@mock_elbv2
@mock_ec2
def test_describe_paginated_balancers():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    for i in range(51):
        conn.create_load_balancer(
            Name='my-lb%d' % i,
            Subnets=[subnet1.id, subnet2.id],
            SecurityGroups=[security_group.id],
            Scheme='internal',
            Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    resp = conn.describe_load_balancers()
    resp['LoadBalancers'].should.have.length_of(50)
    resp['NextMarker'].should.equal(resp['LoadBalancers'][-1]['LoadBalancerName'])
    resp2 = conn.describe_load_balancers(Marker=resp['NextMarker'])
    resp2['LoadBalancers'].should.have.length_of(1)
    assert 'NextToken' not in resp2.keys()


@mock_elbv2
@mock_ec2
def test_delete_load_balancer():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    response = conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    response.get('LoadBalancers').should.have.length_of(1)
    lb = response.get('LoadBalancers')[0]

    conn.delete_load_balancer(LoadBalancerArn=lb.get('LoadBalancerArn'))
    balancers = conn.describe_load_balancers().get('LoadBalancers')
    balancers.should.have.length_of(0)


@mock_ec2
@mock_elbv2
def test_register_targets():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    response = conn.create_target_group(
        Name='a-target',
        Protocol='HTTP',
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol='HTTP',
        HealthCheckPort='8080',
        HealthCheckPath='/',
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={'HttpCode': '200'})
    target_group = response.get('TargetGroups')[0]

    # No targets registered yet
    response = conn.describe_target_health(TargetGroupArn=target_group.get('TargetGroupArn'))
    response.get('TargetHealthDescriptions').should.have.length_of(0)

    response = ec2.create_instances(
        ImageId='ami-1234abcd', MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    response = conn.register_targets(
        TargetGroupArn=target_group.get('TargetGroupArn'),
        Targets=[
            {
                'Id': instance_id1,
                'Port': 5060,
            },
            {
                'Id': instance_id2,
                'Port': 4030,
            },
        ])

    response = conn.describe_target_health(TargetGroupArn=target_group.get('TargetGroupArn'))
    response.get('TargetHealthDescriptions').should.have.length_of(2)

    response = conn.deregister_targets(
        TargetGroupArn=target_group.get('TargetGroupArn'),
        Targets=[{'Id': instance_id2}])

    response = conn.describe_target_health(TargetGroupArn=target_group.get('TargetGroupArn'))
    response.get('TargetHealthDescriptions').should.have.length_of(1)


@mock_ec2
@mock_elbv2
def test_target_group_attributes():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    security_group = ec2.create_security_group(GroupName='a-security-group', Description='First One')
    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')
    subnet1 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1a')
    subnet2 = ec2.create_subnet(VpcId=vpc.id, CidrBlock='172.28.7.192/26', AvailabilityZone='us-east-1b')

    response = conn.create_load_balancer(
        Name='my-lb',
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme='internal',
        Tags=[{'Key': 'key_name', 'Value': 'a_value'}])

    response = conn.create_target_group(
        Name='a-target',
        Protocol='HTTP',
        Port=8080,
        VpcId=vpc.id,
        HealthCheckProtocol='HTTP',
        HealthCheckPort='8080',
        HealthCheckPath='/',
        HealthCheckIntervalSeconds=5,
        HealthCheckTimeoutSeconds=5,
        HealthyThresholdCount=5,
        UnhealthyThresholdCount=2,
        Matcher={'HttpCode': '200'})
    target_group = response.get('TargetGroups')[0]

    # Check it's in the describe_target_groups response
    response = conn.describe_target_groups()
    response.get('TargetGroups').should.have.length_of(1)
    target_group_arn = target_group['TargetGroupArn']

    # The attributes should start with the two defaults
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response['Attributes'].should.have.length_of(2)
    attributes = {attr['Key']: attr['Value'] for attr in response['Attributes']}
    attributes['deregistration_delay.timeout_seconds'].should.equal('300')
    attributes['stickiness.enabled'].should.equal('false')

    # Add cookie stickiness
    response = conn.modify_target_group_attributes(
        TargetGroupArn=target_group_arn,
        Attributes=[
            {
                'Key': 'stickiness.enabled',
                'Value': 'true',
            },
            {
                'Key': 'stickiness.type',
                'Value': 'lb_cookie',
            },
        ])

    # The response should have only the keys updated
    response['Attributes'].should.have.length_of(2)
    attributes = {attr['Key']: attr['Value'] for attr in response['Attributes']}
    attributes['stickiness.type'].should.equal('lb_cookie')
    attributes['stickiness.enabled'].should.equal('true')

    # These new values should be in the full attribute list
    response = conn.describe_target_group_attributes(TargetGroupArn=target_group_arn)
    response['Attributes'].should.have.length_of(3)
    attributes = {attr['Key']: attr['Value'] for attr in response['Attributes']}
    attributes['stickiness.type'].should.equal('lb_cookie')
    attributes['stickiness.enabled'].should.equal('true')
