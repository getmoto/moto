from __future__ import unicode_literals
import boto3
import botocore
import boto
import boto.ec2.elb
from boto.ec2.elb import HealthCheck
from boto.ec2.elb.attributes import (
    ConnectionSettingAttribute,
    ConnectionDrainingAttribute,
    AccessLogAttribute,
)
from botocore.exceptions import ClientError
from boto.exception import BotoServerError
from nose.tools import assert_raises
import sure  # noqa

from moto import mock_elb, mock_ec2, mock_elb_deprecated, mock_ec2_deprecated


@mock_elb_deprecated
@mock_ec2_deprecated
def test_create_load_balancer():
    conn = boto.connect_elb()
    ec2 = boto.ec2.connect_to_region("us-east-1")

    security_group = ec2.create_security_group('sg-abc987', 'description')

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports, scheme='internal', security_groups=[security_group.id])

    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    balancer.name.should.equal("my-lb")
    balancer.scheme.should.equal("internal")
    list(balancer.security_groups).should.equal([security_group.id])
    set(balancer.availability_zones).should.equal(
        set(['us-east-1a', 'us-east-1b']))
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


@mock_elb_deprecated
def test_getting_missing_elb():
    conn = boto.connect_elb()
    conn.get_all_load_balancers.when.called_with(
        load_balancer_names='aaa').should.throw(BotoServerError)


@mock_elb_deprecated
def test_create_elb_in_multiple_region():
    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]

    west1_conn = boto.ec2.elb.connect_to_region("us-west-1")
    west1_conn.create_load_balancer('my-lb', zones, ports)

    west2_conn = boto.ec2.elb.connect_to_region("us-west-2")
    west2_conn.create_load_balancer('my-lb', zones, ports)

    list(west1_conn.get_all_load_balancers()).should.have.length_of(1)
    list(west2_conn.get_all_load_balancers()).should.have.length_of(1)


@mock_elb_deprecated
def test_create_load_balancer_with_certificate():
    conn = boto.connect_elb()

    zones = ['us-east-1a']
    ports = [
        (443, 8443, 'https', 'arn:aws:iam:123456789012:server-certificate/test-cert')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    balancer.name.should.equal("my-lb")
    balancer.scheme.should.equal("internet-facing")
    set(balancer.availability_zones).should.equal(set(['us-east-1a']))
    listener = balancer.listeners[0]
    listener.load_balancer_port.should.equal(443)
    listener.instance_port.should.equal(8443)
    listener.protocol.should.equal("HTTPS")
    listener.ssl_certificate_id.should.equal(
        'arn:aws:iam:123456789012:server-certificate/test-cert')


@mock_elb
def test_create_and_delete_boto3_support():
    client = boto3.client('elb', region_name='us-east-1')

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )
    list(client.describe_load_balancers()[
         'LoadBalancerDescriptions']).should.have.length_of(1)

    client.delete_load_balancer(
        LoadBalancerName='my-lb'
    )
    list(client.describe_load_balancers()[
         'LoadBalancerDescriptions']).should.have.length_of(0)


@mock_elb
def test_create_load_balancer_with_no_listeners_defined():
    client = boto3.client('elb', region_name='us-east-1')

    with assert_raises(ClientError):
        client.create_load_balancer(
            LoadBalancerName='my-lb',
            Listeners=[],
            AvailabilityZones=['us-east-1a', 'us-east-1b']
        )


@mock_elb
def test_describe_paginated_balancers():
    client = boto3.client('elb', region_name='us-east-1')

    for i in range(51):
        client.create_load_balancer(
            LoadBalancerName='my-lb%d' % i,
            Listeners=[
                {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
            AvailabilityZones=['us-east-1a', 'us-east-1b']
        )

    resp = client.describe_load_balancers()
    resp['LoadBalancerDescriptions'].should.have.length_of(50)
    resp['NextMarker'].should.equal(resp['LoadBalancerDescriptions'][-1]['LoadBalancerName'])
    resp2 = client.describe_load_balancers(Marker=resp['NextMarker'])
    resp2['LoadBalancerDescriptions'].should.have.length_of(1)
    assert 'NextToken' not in resp2.keys()


@mock_elb
@mock_ec2
def test_apply_security_groups_to_load_balancer():
    client = boto3.client('elb', region_name='us-east-1')
    ec2 = boto3.resource('ec2', region_name='us-east-1')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    security_group = ec2.create_security_group(
        GroupName='sg01', Description='Test security group sg01', VpcId=vpc.id)

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    response = client.apply_security_groups_to_load_balancer(
        LoadBalancerName='my-lb',
        SecurityGroups=[security_group.id])

    assert response['SecurityGroups'] == [security_group.id]
    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    assert balancer['SecurityGroups'] == [security_group.id]

    # Using a not-real security group raises an error
    with assert_raises(ClientError) as error:
        response = client.apply_security_groups_to_load_balancer(
            LoadBalancerName='my-lb',
            SecurityGroups=['not-really-a-security-group'])
    assert "One or more of the specified security groups do not exist." in str(error.exception)


@mock_elb_deprecated
def test_add_listener():
    conn = boto.connect_elb()
    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http')]
    conn.create_load_balancer('my-lb', zones, ports)
    new_listener = (443, 8443, 'tcp')
    conn.create_load_balancer_listeners('my-lb', [new_listener])
    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    listener2 = balancer.listeners[1]
    listener2.load_balancer_port.should.equal(443)
    listener2.instance_port.should.equal(8443)
    listener2.protocol.should.equal("TCP")


@mock_elb_deprecated
def test_delete_listener():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)
    conn.delete_load_balancer_listeners('my-lb', [443])
    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(80)
    listener1.instance_port.should.equal(8080)
    listener1.protocol.should.equal("HTTP")
    balancer.listeners.should.have.length_of(1)


@mock_elb
def test_create_and_delete_listener_boto3_support():
    client = boto3.client('elb', region_name='us-east-1')

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[{'Protocol': 'http',
                    'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )
    list(client.describe_load_balancers()[
         'LoadBalancerDescriptions']).should.have.length_of(1)

    client.create_load_balancer_listeners(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 443, 'InstancePort': 8443}]
    )
    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    list(balancer['ListenerDescriptions']).should.have.length_of(2)
    balancer['ListenerDescriptions'][0][
        'Listener']['Protocol'].should.equal('HTTP')
    balancer['ListenerDescriptions'][0]['Listener'][
        'LoadBalancerPort'].should.equal(80)
    balancer['ListenerDescriptions'][0]['Listener'][
        'InstancePort'].should.equal(8080)
    balancer['ListenerDescriptions'][1][
        'Listener']['Protocol'].should.equal('TCP')
    balancer['ListenerDescriptions'][1]['Listener'][
        'LoadBalancerPort'].should.equal(443)
    balancer['ListenerDescriptions'][1]['Listener'][
        'InstancePort'].should.equal(8443)

    # Creating this listener with an conflicting definition throws error
    with assert_raises(ClientError):
        client.create_load_balancer_listeners(
            LoadBalancerName='my-lb',
            Listeners=[
                {'Protocol': 'tcp', 'LoadBalancerPort': 443, 'InstancePort': 1234}]
        )

    client.delete_load_balancer_listeners(
        LoadBalancerName='my-lb',
        LoadBalancerPorts=[443])

    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    list(balancer['ListenerDescriptions']).should.have.length_of(1)


@mock_elb_deprecated
def test_set_sslcertificate():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)
    conn.set_lb_listener_SSL_certificate('my-lb', '443', 'arn:certificate')
    balancers = conn.get_all_load_balancers()
    balancer = balancers[0]
    listener1 = balancer.listeners[0]
    listener1.load_balancer_port.should.equal(443)
    listener1.instance_port.should.equal(8443)
    listener1.protocol.should.equal("TCP")
    listener1.ssl_certificate_id.should.equal("arn:certificate")


@mock_elb_deprecated
def test_get_load_balancers_by_name():
    conn = boto.connect_elb()

    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb1', zones, ports)
    conn.create_load_balancer('my-lb2', zones, ports)
    conn.create_load_balancer('my-lb3', zones, ports)

    conn.get_all_load_balancers().should.have.length_of(3)
    conn.get_all_load_balancers(
        load_balancer_names=['my-lb1']).should.have.length_of(1)
    conn.get_all_load_balancers(
        load_balancer_names=['my-lb1', 'my-lb2']).should.have.length_of(2)


@mock_elb_deprecated
def test_delete_load_balancer():
    conn = boto.connect_elb()

    zones = ['us-east-1a']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', zones, ports)

    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(1)

    conn.delete_load_balancer("my-lb")
    balancers = conn.get_all_load_balancers()
    balancers.should.have.length_of(0)


@mock_elb_deprecated
def test_create_health_check():
    conn = boto.connect_elb()

    hc = HealthCheck(
        interval=20,
        healthy_threshold=3,
        unhealthy_threshold=5,
        target='HTTP:8080/health',
        timeout=23,
    )

    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    lb.configure_health_check(hc)

    balancer = conn.get_all_load_balancers()[0]
    health_check = balancer.health_check
    health_check.interval.should.equal(20)
    health_check.healthy_threshold.should.equal(3)
    health_check.unhealthy_threshold.should.equal(5)
    health_check.target.should.equal('HTTP:8080/health')
    health_check.timeout.should.equal(23)


@mock_elb
def test_create_health_check_boto3():
    client = boto3.client('elb', region_name='us-east-1')

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[{'Protocol': 'http',
                    'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )
    client.configure_health_check(
        LoadBalancerName='my-lb',
        HealthCheck={
            'Target': 'HTTP:8080/health',
            'Interval': 20,
            'Timeout': 23,
            'HealthyThreshold': 3,
            'UnhealthyThreshold': 5
        }
    )

    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    balancer['HealthCheck']['Target'].should.equal('HTTP:8080/health')
    balancer['HealthCheck']['Interval'].should.equal(20)
    balancer['HealthCheck']['Timeout'].should.equal(23)
    balancer['HealthCheck']['HealthyThreshold'].should.equal(3)
    balancer['HealthCheck']['UnhealthyThreshold'].should.equal(5)


@mock_ec2_deprecated
@mock_elb_deprecated
def test_register_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    instance_ids = [instance.id for instance in balancer.instances]
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2
@mock_elb
def test_register_instances_boto3():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    response = ec2.create_instances(
        ImageId='ami-1234abcd', MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    client = boto3.client('elb', region_name='us-east-1')
    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[{'Protocol': 'http',
                    'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )
    client.register_instances_with_load_balancer(
        LoadBalancerName='my-lb',
        Instances=[
            {'InstanceId': instance_id1},
            {'InstanceId': instance_id2}
        ]
    )
    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    instance_ids = [instance['InstanceId']
                    for instance in balancer['Instances']]
    set(instance_ids).should.equal(set([instance_id1, instance_id2]))


@mock_ec2_deprecated
@mock_elb_deprecated
def test_deregister_instances():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    lb.register_instances([instance_id1, instance_id2])

    balancer = conn.get_all_load_balancers()[0]
    balancer.instances.should.have.length_of(2)
    balancer.deregister_instances([instance_id1])

    balancer.instances.should.have.length_of(1)
    balancer.instances[0].id.should.equal(instance_id2)


@mock_ec2
@mock_elb
def test_deregister_instances_boto3():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    response = ec2.create_instances(
        ImageId='ami-1234abcd', MinCount=2, MaxCount=2)
    instance_id1 = response[0].id
    instance_id2 = response[1].id

    client = boto3.client('elb', region_name='us-east-1')
    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[{'Protocol': 'http',
                    'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )
    client.register_instances_with_load_balancer(
        LoadBalancerName='my-lb',
        Instances=[
            {'InstanceId': instance_id1},
            {'InstanceId': instance_id2}
        ]
    )

    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    balancer['Instances'].should.have.length_of(2)

    client.deregister_instances_from_load_balancer(
        LoadBalancerName='my-lb',
        Instances=[
            {'InstanceId': instance_id1}
        ]
    )

    balancer = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    balancer['Instances'].should.have.length_of(1)
    balancer['Instances'][0]['InstanceId'].should.equal(instance_id2)


@mock_elb_deprecated
def test_default_attributes():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    attributes = lb.get_attributes()

    attributes.cross_zone_load_balancing.enabled.should.be.false
    attributes.connection_draining.enabled.should.be.false
    attributes.access_log.enabled.should.be.false
    attributes.connecting_settings.idle_timeout.should.equal(60)


@mock_elb_deprecated
def test_cross_zone_load_balancing_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    conn.modify_lb_attribute("my-lb", "CrossZoneLoadBalancing", True)
    attributes = lb.get_attributes(force=True)
    attributes.cross_zone_load_balancing.enabled.should.be.true

    conn.modify_lb_attribute("my-lb", "CrossZoneLoadBalancing", False)
    attributes = lb.get_attributes(force=True)
    attributes.cross_zone_load_balancing.enabled.should.be.false


@mock_elb_deprecated
def test_connection_draining_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    connection_draining = ConnectionDrainingAttribute()
    connection_draining.enabled = True
    connection_draining.timeout = 60

    conn.modify_lb_attribute(
        "my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.enabled.should.be.true
    attributes.connection_draining.timeout.should.equal(60)

    connection_draining.timeout = 30
    conn.modify_lb_attribute(
        "my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.timeout.should.equal(30)

    connection_draining.enabled = False
    conn.modify_lb_attribute(
        "my-lb", "ConnectionDraining", connection_draining)
    attributes = lb.get_attributes(force=True)
    attributes.connection_draining.enabled.should.be.false


@mock_elb_deprecated
def test_access_log_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    access_log = AccessLogAttribute()
    access_log.enabled = True
    access_log.s3_bucket_name = 'bucket'
    access_log.s3_bucket_prefix = 'prefix'
    access_log.emit_interval = 60

    conn.modify_lb_attribute("my-lb", "AccessLog", access_log)
    attributes = lb.get_attributes(force=True)
    attributes.access_log.enabled.should.be.true
    attributes.access_log.s3_bucket_name.should.equal("bucket")
    attributes.access_log.s3_bucket_prefix.should.equal("prefix")
    attributes.access_log.emit_interval.should.equal(60)

    access_log.enabled = False
    conn.modify_lb_attribute("my-lb", "AccessLog", access_log)
    attributes = lb.get_attributes(force=True)
    attributes.access_log.enabled.should.be.false


@mock_elb_deprecated
def test_connection_settings_attribute():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)

    connection_settings = ConnectionSettingAttribute(conn)
    connection_settings.idle_timeout = 120

    conn.modify_lb_attribute(
        "my-lb", "ConnectingSettings", connection_settings)
    attributes = lb.get_attributes(force=True)
    attributes.connecting_settings.idle_timeout.should.equal(120)

    connection_settings.idle_timeout = 60
    conn.modify_lb_attribute(
        "my-lb", "ConnectingSettings", connection_settings)
    attributes = lb.get_attributes(force=True)
    attributes.connecting_settings.idle_timeout.should.equal(60)


@mock_elb_deprecated
def test_create_lb_cookie_stickiness_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    cookie_expiration_period = 60
    policy_name = "LBCookieStickinessPolicy"

    lb.create_cookie_stickiness_policy(cookie_expiration_period, policy_name)

    lb = conn.get_all_load_balancers()[0]
    # There appears to be a quirk about boto, whereby it returns a unicode
    # string for cookie_expiration_period, despite being stated in
    # documentation to be a long numeric.
    #
    # To work around that, this value is converted to an int and checked.
    cookie_expiration_period_response_str = lb.policies.lb_cookie_stickiness_policies[
        0].cookie_expiration_period
    int(cookie_expiration_period_response_str).should.equal(
        cookie_expiration_period)
    lb.policies.lb_cookie_stickiness_policies[
        0].policy_name.should.equal(policy_name)


@mock_elb_deprecated
def test_create_lb_cookie_stickiness_policy_no_expiry():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    policy_name = "LBCookieStickinessPolicy"

    lb.create_cookie_stickiness_policy(None, policy_name)

    lb = conn.get_all_load_balancers()[0]
    lb.policies.lb_cookie_stickiness_policies[
        0].cookie_expiration_period.should.be.none
    lb.policies.lb_cookie_stickiness_policies[
        0].policy_name.should.equal(policy_name)


@mock_elb_deprecated
def test_create_app_cookie_stickiness_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    cookie_name = "my-stickiness-policy"
    policy_name = "AppCookieStickinessPolicy"

    lb.create_app_cookie_stickiness_policy(cookie_name, policy_name)

    lb = conn.get_all_load_balancers()[0]
    lb.policies.app_cookie_stickiness_policies[
        0].cookie_name.should.equal(cookie_name)
    lb.policies.app_cookie_stickiness_policies[
        0].policy_name.should.equal(policy_name)


@mock_elb_deprecated
def test_create_lb_policy():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    policy_name = "ProxyPolicy"

    lb.create_lb_policy(policy_name, 'ProxyProtocolPolicyType', {
                        'ProxyProtocol': True})

    lb = conn.get_all_load_balancers()[0]
    lb.policies.other_policies[0].policy_name.should.equal(policy_name)


@mock_elb_deprecated
def test_set_policies_of_listener():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    listener_port = 80
    policy_name = "my-stickiness-policy"

    # boto docs currently state that zero or one policy may be associated
    # with a given listener

    # in a real flow, it is necessary first to create a policy,
    # then to set that policy to the listener
    lb.create_cookie_stickiness_policy(None, policy_name)
    lb.set_policies_of_listener(listener_port, [policy_name])

    lb = conn.get_all_load_balancers()[0]
    listener = lb.listeners[0]
    listener.load_balancer_port.should.equal(listener_port)
    # by contrast to a backend, a listener stores only policy name strings
    listener.policy_names[0].should.equal(policy_name)


@mock_elb_deprecated
def test_set_policies_of_backend_server():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', [], ports)
    instance_port = 8080
    policy_name = "ProxyPolicy"

    # in a real flow, it is necessary first to create a policy,
    # then to set that policy to the backend
    lb.create_lb_policy(policy_name, 'ProxyProtocolPolicyType', {
                        'ProxyProtocol': True})
    lb.set_policies_of_backend_server(instance_port, [policy_name])

    lb = conn.get_all_load_balancers()[0]
    backend = lb.backends[0]
    backend.instance_port.should.equal(instance_port)
    # by contrast to a listener, a backend stores OtherPolicy objects
    backend.policies[0].policy_name.should.equal(policy_name)


@mock_ec2_deprecated
@mock_elb_deprecated
def test_describe_instance_health():
    ec2_conn = boto.connect_ec2()
    reservation = ec2_conn.run_instances('ami-1234abcd', 2)
    instance_id1 = reservation.instances[0].id
    instance_id2 = reservation.instances[1].id

    conn = boto.connect_elb()
    zones = ['us-east-1a', 'us-east-1b']
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    lb = conn.create_load_balancer('my-lb', zones, ports)

    instances_health = conn.describe_instance_health('my-lb')
    instances_health.should.be.empty

    lb.register_instances([instance_id1, instance_id2])

    instances_health = conn.describe_instance_health('my-lb')
    instances_health.should.have.length_of(2)
    for instance_health in instances_health:
        instance_health.instance_id.should.be.within(
            [instance_id1, instance_id2])
        instance_health.state.should.equal('InService')

    instances_health = conn.describe_instance_health('my-lb', [instance_id1])
    instances_health.should.have.length_of(1)
    instances_health[0].instance_id.should.equal(instance_id1)
    instances_health[0].state.should.equal('InService')


@mock_ec2
@mock_elb
def test_describe_instance_health_boto3():
    elb = boto3.client('elb', region_name="us-east-1")
    ec2 = boto3.client('ec2', region_name="us-east-1")
    instances = ec2.run_instances(MinCount=2, MaxCount=2)['Instances']
    lb_name = "my_load_balancer"
    elb.create_load_balancer(
        Listeners=[{
            'InstancePort': 80,
            'LoadBalancerPort': 8080,
            'Protocol': 'HTTP'
        }],
        LoadBalancerName=lb_name,
    )
    elb.register_instances_with_load_balancer(
        LoadBalancerName=lb_name,
        Instances=[{'InstanceId': instances[0]['InstanceId']}]
    )
    instances_health = elb.describe_instance_health(
        LoadBalancerName=lb_name,
        Instances=[{'InstanceId': instance['InstanceId']} for instance in instances]
    )
    instances_health['InstanceStates'].should.have.length_of(2)
    instances_health['InstanceStates'][0]['InstanceId'].\
        should.equal(instances[0]['InstanceId'])
    instances_health['InstanceStates'][0]['State'].\
        should.equal('InService')
    instances_health['InstanceStates'][1]['InstanceId'].\
        should.equal(instances[1]['InstanceId'])
    instances_health['InstanceStates'][1]['State'].\
        should.equal('Unknown')


@mock_elb
def test_add_remove_tags():
    client = boto3.client('elb', region_name='us-east-1')

    client.add_tags.when.called_with(LoadBalancerNames=['my-lb'],
                                     Tags=[{
                                         'Key': 'a',
                                         'Value': 'b'
                                     }]).should.throw(botocore.exceptions.ClientError)

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    list(client.describe_load_balancers()[
         'LoadBalancerDescriptions']).should.have.length_of(1)

    client.add_tags(LoadBalancerNames=['my-lb'],
                    Tags=[{
                        'Key': 'a',
                        'Value': 'b'
                    }])

    tags = dict([(d['Key'], d['Value']) for d in client.describe_tags(
        LoadBalancerNames=['my-lb'])['TagDescriptions'][0]['Tags']])
    tags.should.have.key('a').which.should.equal('b')

    client.add_tags(LoadBalancerNames=['my-lb'],
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
                        'Key': 'i',
                        'Value': 'b'
                    }, {
                        'Key': 'j',
                        'Value': 'b'
                    }])

    client.add_tags.when.called_with(LoadBalancerNames=['my-lb'],
                                     Tags=[{
                                         'Key': 'k',
                                         'Value': 'b'
                                     }]).should.throw(botocore.exceptions.ClientError)

    client.add_tags(LoadBalancerNames=['my-lb'],
                    Tags=[{
                        'Key': 'j',
                        'Value': 'c'
                    }])

    tags = dict([(d['Key'], d['Value']) for d in client.describe_tags(
        LoadBalancerNames=['my-lb'])['TagDescriptions'][0]['Tags']])

    tags.should.have.key('a').which.should.equal('b')
    tags.should.have.key('b').which.should.equal('b')
    tags.should.have.key('c').which.should.equal('b')
    tags.should.have.key('d').which.should.equal('b')
    tags.should.have.key('e').which.should.equal('b')
    tags.should.have.key('f').which.should.equal('b')
    tags.should.have.key('g').which.should.equal('b')
    tags.should.have.key('h').which.should.equal('b')
    tags.should.have.key('i').which.should.equal('b')
    tags.should.have.key('j').which.should.equal('c')
    tags.shouldnt.have.key('k')

    client.remove_tags(LoadBalancerNames=['my-lb'],
                       Tags=[{
                           'Key': 'a'
                       }])

    tags = dict([(d['Key'], d['Value']) for d in client.describe_tags(
        LoadBalancerNames=['my-lb'])['TagDescriptions'][0]['Tags']])

    tags.shouldnt.have.key('a')
    tags.should.have.key('b').which.should.equal('b')
    tags.should.have.key('c').which.should.equal('b')
    tags.should.have.key('d').which.should.equal('b')
    tags.should.have.key('e').which.should.equal('b')
    tags.should.have.key('f').which.should.equal('b')
    tags.should.have.key('g').which.should.equal('b')
    tags.should.have.key('h').which.should.equal('b')
    tags.should.have.key('i').which.should.equal('b')
    tags.should.have.key('j').which.should.equal('c')

    client.create_load_balancer(
        LoadBalancerName='other-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 433, 'InstancePort': 8433}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    client.add_tags(LoadBalancerNames=['other-lb'],
                    Tags=[{
                        'Key': 'other',
                        'Value': 'something'
                    }])

    lb_tags = dict([(l['LoadBalancerName'], dict([(d['Key'], d['Value']) for d in l['Tags']]))
                    for l in client.describe_tags(LoadBalancerNames=['my-lb', 'other-lb'])['TagDescriptions']])

    lb_tags.should.have.key('my-lb')
    lb_tags.should.have.key('other-lb')

    lb_tags['my-lb'].shouldnt.have.key('other')
    lb_tags[
        'other-lb'].should.have.key('other').which.should.equal('something')


@mock_elb
def test_create_with_tags():
    client = boto3.client('elb', region_name='us-east-1')

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b'],
        Tags=[{
            'Key': 'k',
            'Value': 'v'
        }]
    )

    tags = dict((d['Key'], d['Value']) for d in client.describe_tags(
        LoadBalancerNames=['my-lb'])['TagDescriptions'][0]['Tags'])
    tags.should.have.key('k').which.should.equal('v')


@mock_elb
def test_modify_attributes():
    client = boto3.client('elb', region_name='us-east-1')

    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[{'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        AvailabilityZones=['us-east-1a', 'us-east-1b']
    )

    # Default ConnectionDraining timeout of 300 seconds
    client.modify_load_balancer_attributes(
        LoadBalancerName='my-lb',
        LoadBalancerAttributes={
            'ConnectionDraining': {'Enabled': True},
        }
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName='my-lb')
    lb_attrs['LoadBalancerAttributes']['ConnectionDraining']['Enabled'].should.equal(True)
    lb_attrs['LoadBalancerAttributes']['ConnectionDraining']['Timeout'].should.equal(300)

    # specify a custom ConnectionDraining timeout
    client.modify_load_balancer_attributes(
        LoadBalancerName='my-lb',
        LoadBalancerAttributes={
            'ConnectionDraining': {
                'Enabled': True,
                'Timeout': 45,
            },
        }
    )
    lb_attrs = client.describe_load_balancer_attributes(LoadBalancerName='my-lb')
    lb_attrs['LoadBalancerAttributes']['ConnectionDraining']['Enabled'].should.equal(True)
    lb_attrs['LoadBalancerAttributes']['ConnectionDraining']['Timeout'].should.equal(45)


@mock_ec2
@mock_elb
def test_subnets():
    ec2 = boto3.resource('ec2', region_name='us-east-1')
    vpc = ec2.create_vpc(
        CidrBlock='172.28.7.0/24',
        InstanceTenancy='default'
    )
    subnet = ec2.create_subnet(
        VpcId=vpc.id,
        CidrBlock='172.28.7.192/26'
    )
    client = boto3.client('elb', region_name='us-east-1')
    client.create_load_balancer(
        LoadBalancerName='my-lb',
        Listeners=[
            {'Protocol': 'tcp', 'LoadBalancerPort': 80, 'InstancePort': 8080}],
        Subnets=[subnet.id]
    )

    lb = client.describe_load_balancers()['LoadBalancerDescriptions'][0]
    lb.should.have.key('Subnets').which.should.have.length_of(1)
    lb['Subnets'][0].should.equal(subnet.id)

    lb.should.have.key('VPCId').which.should.equal(vpc.id)


@mock_elb_deprecated
def test_create_load_balancer_duplicate():
    conn = boto.connect_elb()
    ports = [(80, 8080, 'http'), (443, 8443, 'tcp')]
    conn.create_load_balancer('my-lb', [], ports)
    conn.create_load_balancer.when.called_with(
        'my-lb', [], ports).should.throw(BotoServerError)
