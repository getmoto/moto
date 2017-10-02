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
    target_group_arn = target_group['TargetGroupArn']

    # Add tags to the target group
    conn.add_tags(ResourceArns=[target_group_arn], Tags=[{'Key': 'target', 'Value': 'group'}])
    conn.describe_tags(ResourceArns=[target_group_arn])['TagDescriptions'][0]['Tags'].should.equal(
        [{'Key': 'target', 'Value': 'group'}])

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
def test_create_invalid_target_group():
    conn = boto3.client('elbv2', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='172.28.7.0/24', InstanceTenancy='default')

    # Fail to create target group with name which length is 33
    long_name = 'A' * 33
    with assert_raises(ClientError):
        conn.create_target_group(
            Name=long_name,
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

    invalid_names = ['-name', 'name-', '-name-', 'example.com', 'test@test', 'Na--me']
    for name in invalid_names:
        with assert_raises(ClientError):
            conn.create_target_group(
                Name=name,
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

    valid_names = ['name', 'Name', '000']
    for name in valid_names:
        conn.create_target_group(
            Name=name,
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

    # check if Names filter works
    response = conn.describe_target_groups(Names=[])
    response = conn.describe_target_groups(Names=['a-target'])
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


@mock_elbv2
@mock_ec2
def test_handle_listener_rules():
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

    # create first rule
    priority = 100
    host = 'xxx.example.com'
    path_pattern = 'foobar'
    created_rule = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=priority,
        Conditions=[{
            'Field': 'host-header',
            'Values': [ host ]
        },
        {
            'Field': 'path-pattern',
            'Values': [ path_pattern ]
        }],
        Actions=[{
            'TargetGroupArn': target_group.get('TargetGroupArn'),
            'Type': 'forward'
        }]
    )['Rules'][0]
    created_rule['Priority'].should.equal('100')

    # check if rules is sorted by priority
    priority = 50
    host = 'yyy.example.com'
    path_pattern = 'foobar'
    rules = conn.create_rule(
        ListenerArn=http_listener_arn,
        Priority=priority,
        Conditions=[{
            'Field': 'host-header',
            'Values': [ host ]
        },
        {
            'Field': 'path-pattern',
            'Values': [ path_pattern ]
        }],
        Actions=[{
            'TargetGroupArn': target_group.get('TargetGroupArn'),
            'Type': 'forward'
        }]
    )

    # test for PriorityInUse
    host2 = 'yyy.example.com'
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=priority,
            Conditions=[{
                'Field': 'host-header',
                'Values': [ host ]
            },
            {
                'Field': 'path-pattern',
                'Values': [ path_pattern ]
            }],
            Actions=[{
                'TargetGroupArn': target_group.get('TargetGroupArn'),
                'Type': 'forward'
            }]
        )


    # test for describe listeners
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn)
    len(obtained_rules['Rules']).should.equal(3)
    priorities = [rule['Priority'] for rule in obtained_rules['Rules']]
    priorities.should.equal(['50', '100', 'default'])

    first_rule = obtained_rules['Rules'][0]
    second_rule = obtained_rules['Rules'][1]
    obtained_rules = conn.describe_rules(RuleArns=[first_rule['RuleArn']])
    obtained_rules['Rules'].should.equal([first_rule])

    # test for pagination
    obtained_rules = conn.describe_rules(ListenerArn=http_listener_arn, PageSize=1)
    len(obtained_rules['Rules']).should.equal(1)
    obtained_rules.should.have.key('NextMarker')
    next_marker = obtained_rules['NextMarker']

    following_rules = conn.describe_rules(ListenerArn=http_listener_arn, PageSize=1, Marker=next_marker)
    len(following_rules['Rules']).should.equal(1)
    following_rules.should.have.key('NextMarker')
    following_rules['Rules'][0]['RuleArn'].should_not.equal(obtained_rules['Rules'][0]['RuleArn'])

    # test for invalid describe rule request
    with assert_raises(ClientError):
        conn.describe_rules()
    with assert_raises(ClientError):
        conn.describe_rules(RuleArns=[])
    with assert_raises(ClientError):
        conn.describe_rules(
            ListenerArn=http_listener_arn,
            RuleArns=[first_rule['RuleArn']]
        )

    # modify rule partially
    new_host = 'new.example.com'
    new_path_pattern = 'new_path'
    modified_rule = conn.modify_rule(
        RuleArn=first_rule['RuleArn'],
        Conditions=[{
                'Field': 'host-header',
                'Values': [ new_host ]
            },
            {
                'Field': 'path-pattern',
                'Values': [ new_path_pattern ]
            }]
    )['Rules'][0]

    rules = conn.describe_rules(ListenerArn=http_listener_arn)
    obtained_rule = rules['Rules'][0]
    modified_rule.should.equal(obtained_rule)
    obtained_rule['Conditions'][0]['Values'][0].should.equal(new_host)
    obtained_rule['Conditions'][1]['Values'][0].should.equal(new_path_pattern)
    obtained_rule['Actions'][0]['TargetGroupArn'].should.equal(target_group.get('TargetGroupArn'))

    # modify priority
    conn.set_rule_priorities(
        RulePriorities=[
            {'RuleArn': first_rule['RuleArn'], 'Priority': int(first_rule['Priority']) - 1}
        ]
    )
    with assert_raises(ClientError):
        conn.set_rule_priorities(
            RulePriorities=[
                {'RuleArn': first_rule['RuleArn'], 'Priority': 999},
                {'RuleArn': second_rule['RuleArn'], 'Priority': 999}
            ]
        )

    # delete
    arn = first_rule['RuleArn']
    conn.delete_rule(RuleArn=arn)
    rules = conn.describe_rules(ListenerArn=http_listener_arn)['Rules']
    len(rules).should.equal(2)

    # test for invalid action type
    safe_priority = 2
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{
                'Field': 'host-header',
                'Values': [ host ]
            },
            {
                'Field': 'path-pattern',
                'Values': [ path_pattern ]
            }],
            Actions=[{
                'TargetGroupArn': target_group.get('TargetGroupArn'),
                'Type': 'forward2'
            }]
        )

    # test for invalid action type
    safe_priority = 2
    invalid_target_group_arn = target_group.get('TargetGroupArn') + 'x'
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{
                'Field': 'host-header',
                'Values': [ host ]
            },
            {
                'Field': 'path-pattern',
                'Values': [ path_pattern ]
            }],
            Actions=[{
                'TargetGroupArn': invalid_target_group_arn,
                'Type': 'forward'
            }]
        )

    # test for invalid condition field_name
    safe_priority = 2
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{
                'Field': 'xxxxxxx',
                'Values': [ host ]
            }],
            Actions=[{
                'TargetGroupArn': target_group.get('TargetGroupArn'),
                'Type': 'forward'
            }]
        )

    # test for emptry condition value
    safe_priority = 2
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{
                'Field': 'host-header',
                'Values': []
            }],
            Actions=[{
                'TargetGroupArn': target_group.get('TargetGroupArn'),
                'Type': 'forward'
            }]
        )

    # test for multiple condition value
    safe_priority = 2
    with assert_raises(ClientError):
        r = conn.create_rule(
            ListenerArn=http_listener_arn,
            Priority=safe_priority,
            Conditions=[{
                'Field': 'host-header',
                'Values': [host, host]
            }],
            Actions=[{
                'TargetGroupArn': target_group.get('TargetGroupArn'),
                'Type': 'forward'
            }]
        )


@mock_elbv2
@mock_ec2
def test_describe_invalid_target_group():
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

    # Check error raises correctly
    with assert_raises(ClientError):
        conn.describe_target_groups(Names=['invalid'])
