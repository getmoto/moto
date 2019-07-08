from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
from botocore.exceptions import ClientError

import tests.backport_assert_raises
from nose.tools import assert_raises

import base64
import datetime
import ipaddress

import six
import boto
import boto3
from boto.ec2.instance import Reservation, InstanceAttribute
from boto.exception import EC2ResponseError, EC2ResponseError
from freezegun import freeze_time
import sure  # noqa

from moto import mock_ec2_deprecated, mock_ec2
from tests.helpers import requires_boto_gte


################ Test Readme ###############
def add_servers(ami_id, count):
    conn = boto.connect_ec2()
    for index in range(count):
        conn.run_instances(ami_id)


@mock_ec2_deprecated
def test_add_servers():
    add_servers('ami-1234abcd', 2)

    conn = boto.connect_ec2()
    reservations = conn.get_all_instances()
    assert len(reservations) == 2
    instance1 = reservations[0].instances[0]
    assert instance1.image_id == 'ami-1234abcd'

############################################


@freeze_time("2014-01-01 05:00:00")
@mock_ec2_deprecated
def test_instance_launch_and_terminate():
    conn = boto.ec2.connect_to_region("us-east-1")

    with assert_raises(EC2ResponseError) as ex:
        reservation = conn.run_instances('ami-1234abcd', dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the RunInstance operation: Request would have succeeded, but DryRun flag is set')

    reservation = conn.run_instances('ami-1234abcd')
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]
    instance.state.should.equal('pending')

    reservations = conn.get_all_instances()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instance = instances[0]
    instance.id.should.equal(instance.id)
    instance.state.should.equal('running')
    instance.launch_time.should.equal("2014-01-01T05:00:00.000Z")
    instance.vpc_id.should.equal(None)
    instance.placement.should.equal('us-east-1a')

    root_device_name = instance.root_device_name
    instance.block_device_mapping[
        root_device_name].status.should.equal('in-use')
    volume_id = instance.block_device_mapping[root_device_name].volume_id
    volume_id.should.match(r'vol-\w+')

    volume = conn.get_all_volumes(volume_ids=[volume_id])[0]
    volume.attach_data.instance_id.should.equal(instance.id)
    volume.status.should.equal('in-use')

    with assert_raises(EC2ResponseError) as ex:
        conn.terminate_instances([instance.id], dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the TerminateInstance operation: Request would have succeeded, but DryRun flag is set')

    conn.terminate_instances([instance.id])

    reservations = conn.get_all_instances()
    instance = reservations[0].instances[0]
    instance.state.should.equal('terminated')


@mock_ec2_deprecated
def test_terminate_empty_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.terminate_instances.when.called_with(
        []).should.throw(EC2ResponseError)


@freeze_time("2014-01-01 05:00:00")
@mock_ec2_deprecated
def test_instance_attach_volume():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    vol1 = conn.create_volume(size=36, zone=conn.region.name)
    vol1.attach(instance.id, "/dev/sda1")
    vol1.update()
    vol2 = conn.create_volume(size=65, zone=conn.region.name)
    vol2.attach(instance.id, "/dev/sdb1")
    vol2.update()
    vol3 = conn.create_volume(size=130, zone=conn.region.name)
    vol3.attach(instance.id, "/dev/sdc1")
    vol3.update()

    reservations = conn.get_all_instances()
    instance = reservations[0].instances[0]

    instance.block_device_mapping.should.have.length_of(3)

    for v in conn.get_all_volumes(volume_ids=[instance.block_device_mapping['/dev/sdc1'].volume_id]):
        v.attach_data.instance_id.should.equal(instance.id)
        # can do due to freeze_time decorator.
        v.attach_data.attach_time.should.equal(instance.launch_time)
        # can do due to freeze_time decorator.
        v.create_time.should.equal(instance.launch_time)
        v.region.name.should.equal(instance.region.name)
        v.status.should.equal('in-use')


@mock_ec2_deprecated
def test_get_instances_by_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instance1, instance2 = reservation.instances

    reservations = conn.get_all_instances(instance_ids=[instance1.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(1)
    reservation.instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(
        instance_ids=[instance1.id, instance2.id])
    reservations.should.have.length_of(1)
    reservation = reservations[0]
    reservation.instances.should.have.length_of(2)
    instance_ids = [instance.id for instance in reservation.instances]
    instance_ids.should.equal([instance1.id, instance2.id])

    # Call get_all_instances with a bad id should raise an error
    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_instances(instance_ids=[instance1.id, "i-1234abcd"])
    cm.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_get_paginated_instances():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-east-1')
    conn = boto3.resource('ec2', 'us-east-1')
    for i in range(100):
        conn.create_instances(ImageId=image_id,
                              MinCount=1,
                              MaxCount=1)
    resp = client.describe_instances(MaxResults=50)
    reservations = resp['Reservations']
    reservations.should.have.length_of(50)
    next_token = resp['NextToken']
    next_token.should_not.be.none
    resp2 = client.describe_instances(NextToken=next_token)
    reservations.extend(resp2['Reservations'])
    reservations.should.have.length_of(100)
    assert 'NextToken' not in resp2.keys()


@mock_ec2
def test_create_with_tags():
    ec2 = boto3.client('ec2', region_name='us-west-2')
    instances = ec2.run_instances(
        ImageId='ami-123',
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG1',
                        'Value': 'MY_VALUE1',
                    },
                    {
                        'Key': 'MY_TAG2',
                        'Value': 'MY_VALUE2',
                    },
                ],
            },
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'MY_TAG3',
                        'Value': 'MY_VALUE3',
                    },
                ]
            },
        ],
    )
    assert 'Tags' in instances['Instances'][0]
    len(instances['Instances'][0]['Tags']).should.equal(3)


@mock_ec2_deprecated
def test_get_instances_filtering_by_state():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances

    conn.terminate_instances([instance1.id])

    reservations = conn.get_all_instances(
        filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    # Since we terminated instance1, only instance2 and instance3 should be
    # returned
    instance_ids = [instance.id for instance in reservations[0].instances]
    set(instance_ids).should.equal(set([instance2.id, instance3.id]))

    reservations = conn.get_all_instances(
        [instance2.id], filters={'instance-state-name': 'running'})
    reservations.should.have.length_of(1)
    instance_ids = [instance.id for instance in reservations[0].instances]
    instance_ids.should.equal([instance2.id])

    reservations = conn.get_all_instances(
        [instance2.id], filters={'instance-state-name': 'terminated'})
    list(reservations).should.equal([])

    # get_all_instances should still return all 3
    reservations = conn.get_all_instances()
    reservations[0].instances.should.have.length_of(3)

    conn.get_all_instances.when.called_with(
        filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)


@mock_ec2_deprecated
def test_get_instances_filtering_by_instance_id():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances

    reservations = conn.get_all_instances(
        filters={'instance-id': instance1.id})
    # get_all_instances should return just instance1
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(
        filters={'instance-id': [instance1.id, instance2.id]})
    # get_all_instances should return two
    reservations[0].instances.should.have.length_of(2)

    reservations = conn.get_all_instances(
        filters={'instance-id': 'non-existing-id'})
    reservations.should.have.length_of(0)


@mock_ec2_deprecated
def test_get_instances_filtering_by_instance_type():
    conn = boto.connect_ec2()
    reservation1 = conn.run_instances('ami-1234abcd', instance_type='m1.small')
    instance1 = reservation1.instances[0]
    reservation2 = conn.run_instances('ami-1234abcd', instance_type='m1.small')
    instance2 = reservation2.instances[0]
    reservation3 = conn.run_instances('ami-1234abcd', instance_type='t1.micro')
    instance3 = reservation3.instances[0]

    reservations = conn.get_all_instances(
        filters={'instance-type': 'm1.small'})
    # get_all_instances should return instance1,2
    reservations.should.have.length_of(2)
    reservations[0].instances.should.have.length_of(1)
    reservations[1].instances.should.have.length_of(1)
    instance_ids = [reservations[0].instances[0].id,
                    reservations[1].instances[0].id]
    set(instance_ids).should.equal(set([instance1.id, instance2.id]))

    reservations = conn.get_all_instances(
        filters={'instance-type': 't1.micro'})
    # get_all_instances should return one
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance3.id)

    reservations = conn.get_all_instances(
        filters={'instance-type': ['t1.micro', 'm1.small']})
    reservations.should.have.length_of(3)
    reservations[0].instances.should.have.length_of(1)
    reservations[1].instances.should.have.length_of(1)
    reservations[2].instances.should.have.length_of(1)
    instance_ids = [
        reservations[0].instances[0].id,
        reservations[1].instances[0].id,
        reservations[2].instances[0].id,
    ]
    set(instance_ids).should.equal(
        set([instance1.id, instance2.id, instance3.id]))

    reservations = conn.get_all_instances(filters={'instance-type': 'bogus'})
    # bogus instance-type should return none
    reservations.should.have.length_of(0)


@mock_ec2_deprecated
def test_get_instances_filtering_by_reason_code():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.stop()
    instance2.terminate()

    reservations = conn.get_all_instances(
        filters={'state-reason-code': 'Client.UserInitiatedShutdown'})
    # get_all_instances should return instance1 and instance2
    reservations[0].instances.should.have.length_of(2)
    set([instance1.id, instance2.id]).should.equal(
        set([i.id for i in reservations[0].instances]))

    reservations = conn.get_all_instances(filters={'state-reason-code': ''})
    # get_all_instances should return instance 3
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance3.id)


@mock_ec2_deprecated
def test_get_instances_filtering_by_source_dest_check():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instance1, instance2 = reservation.instances
    conn.modify_instance_attribute(
        instance1.id, attribute='sourceDestCheck', value=False)

    source_dest_check_false = conn.get_all_instances(
        filters={'source-dest-check': 'false'})
    source_dest_check_true = conn.get_all_instances(
        filters={'source-dest-check': 'true'})

    source_dest_check_false[0].instances.should.have.length_of(1)
    source_dest_check_false[0].instances[0].id.should.equal(instance1.id)

    source_dest_check_true[0].instances.should.have.length_of(1)
    source_dest_check_true[0].instances[0].id.should.equal(instance2.id)


@mock_ec2_deprecated
def test_get_instances_filtering_by_vpc_id():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc1 = conn.create_vpc("10.0.0.0/16")
    subnet1 = conn.create_subnet(vpc1.id, "10.0.0.0/27")
    reservation1 = conn.run_instances(
        'ami-1234abcd', min_count=1, subnet_id=subnet1.id)
    instance1 = reservation1.instances[0]

    vpc2 = conn.create_vpc("10.1.0.0/16")
    subnet2 = conn.create_subnet(vpc2.id, "10.1.0.0/27")
    reservation2 = conn.run_instances(
        'ami-1234abcd', min_count=1, subnet_id=subnet2.id)
    instance2 = reservation2.instances[0]

    reservations1 = conn.get_all_instances(filters={'vpc-id': vpc1.id})
    reservations1.should.have.length_of(1)
    reservations1[0].instances.should.have.length_of(1)
    reservations1[0].instances[0].id.should.equal(instance1.id)
    reservations1[0].instances[0].vpc_id.should.equal(vpc1.id)
    reservations1[0].instances[0].subnet_id.should.equal(subnet1.id)

    reservations2 = conn.get_all_instances(filters={'vpc-id': vpc2.id})
    reservations2.should.have.length_of(1)
    reservations2[0].instances.should.have.length_of(1)
    reservations2[0].instances[0].id.should.equal(instance2.id)
    reservations2[0].instances[0].vpc_id.should.equal(vpc2.id)
    reservations2[0].instances[0].subnet_id.should.equal(subnet2.id)


@mock_ec2_deprecated
def test_get_instances_filtering_by_architecture():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=1)
    instance = reservation.instances

    reservations = conn.get_all_instances(filters={'architecture': 'x86_64'})
    # get_all_instances should return the instance
    reservations[0].instances.should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_image_id():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-east-1')
    conn = boto3.resource('ec2', 'us-east-1')
    conn.create_instances(ImageId=image_id,
                          MinCount=1,
                          MaxCount=1)

    reservations = client.describe_instances(Filters=[{'Name': 'image-id',
                                                       'Values': [image_id]}])['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_private_dns():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-east-1')
    conn = boto3.resource('ec2', 'us-east-1')
    conn.create_instances(ImageId=image_id,
                          MinCount=1,
                          MaxCount=1,
                          PrivateIpAddress='10.0.0.1')
    reservations = client.describe_instances(Filters=[
        {'Name': 'private-dns-name', 'Values': ['ip-10-0-0-1.ec2.internal']}
    ])['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_ni_private_dns():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-west-2')
    conn = boto3.resource('ec2', 'us-west-2')
    conn.create_instances(ImageId=image_id,
                          MinCount=1,
                          MaxCount=1,
                          PrivateIpAddress='10.0.0.1')
    reservations = client.describe_instances(Filters=[
        {'Name': 'network-interface.private-dns-name', 'Values': ['ip-10-0-0-1.us-west-2.compute.internal']}
    ])['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_instance_group_name():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-east-1')
    client.create_security_group(
        Description='test',
        GroupName='test_sg'
    )
    client.run_instances(ImageId=image_id,
                          MinCount=1,
                          MaxCount=1,
                          SecurityGroups=['test_sg'])
    reservations = client.describe_instances(Filters=[
        {'Name': 'instance.group-name', 'Values': ['test_sg']}
    ])['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)


@mock_ec2
def test_get_instances_filtering_by_instance_group_id():
    image_id = 'ami-1234abcd'
    client = boto3.client('ec2', region_name='us-east-1')
    create_sg = client.create_security_group(
        Description='test',
        GroupName='test_sg'
    )
    group_id = create_sg['GroupId']
    client.run_instances(ImageId=image_id,
                          MinCount=1,
                          MaxCount=1,
                          SecurityGroups=['test_sg'])
    reservations = client.describe_instances(Filters=[
        {'Name': 'instance.group-id', 'Values': [group_id]}
    ])['Reservations']
    reservations[0]['Instances'].should.have.length_of(1)


@mock_ec2_deprecated
def test_get_instances_filtering_by_tag():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag('tag1', 'value1')
    instance1.add_tag('tag2', 'value2')
    instance2.add_tag('tag1', 'value1')
    instance2.add_tag('tag2', 'wrong value')
    instance3.add_tag('tag2', 'value2')

    reservations = conn.get_all_instances(filters={'tag:tag0': 'value0'})
    # get_all_instances should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_instances(filters={'tag:tag1': 'value1'})
    # get_all_instances should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_instances(
        filters={'tag:tag1': 'value1', 'tag:tag2': 'value2'})
    # get_all_instances should return the instance with both tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(
        filters={'tag:tag1': 'value1', 'tag:tag2': 'value2'})
    # get_all_instances should return the instance with both tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(1)
    reservations[0].instances[0].id.should.equal(instance1.id)

    reservations = conn.get_all_instances(
        filters={'tag:tag2': ['value2', 'bogus']})
    # get_all_instances should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance3.id)


@mock_ec2_deprecated
def test_get_instances_filtering_by_tag_value():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag('tag1', 'value1')
    instance1.add_tag('tag2', 'value2')
    instance2.add_tag('tag1', 'value1')
    instance2.add_tag('tag2', 'wrong value')
    instance3.add_tag('tag2', 'value2')

    reservations = conn.get_all_instances(filters={'tag-value': 'value0'})
    # get_all_instances should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_instances(filters={'tag-value': 'value1'})
    # get_all_instances should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_instances(
        filters={'tag-value': ['value2', 'value1']})
    # get_all_instances should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(3)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)
    reservations[0].instances[2].id.should.equal(instance3.id)

    reservations = conn.get_all_instances(
        filters={'tag-value': ['value2', 'bogus']})
    # get_all_instances should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance3.id)


@mock_ec2_deprecated
def test_get_instances_filtering_by_tag_name():
    conn = boto.connect_ec2()
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.add_tag('tag1')
    instance1.add_tag('tag2')
    instance2.add_tag('tag1')
    instance2.add_tag('tag2X')
    instance3.add_tag('tag3')

    reservations = conn.get_all_instances(filters={'tag-key': 'tagX'})
    # get_all_instances should return no instances
    reservations.should.have.length_of(0)

    reservations = conn.get_all_instances(filters={'tag-key': 'tag1'})
    # get_all_instances should return both instances with this tag value
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(2)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)

    reservations = conn.get_all_instances(
        filters={'tag-key': ['tag1', 'tag3']})
    # get_all_instances should return both instances with one of the
    # acceptable tag values
    reservations.should.have.length_of(1)
    reservations[0].instances.should.have.length_of(3)
    reservations[0].instances[0].id.should.equal(instance1.id)
    reservations[0].instances[1].id.should.equal(instance2.id)
    reservations[0].instances[2].id.should.equal(instance3.id)


@mock_ec2_deprecated
def test_instance_start_and_stop():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', min_count=2)
    instances = reservation.instances
    instances.should.have.length_of(2)

    instance_ids = [instance.id for instance in instances]

    with assert_raises(EC2ResponseError) as ex:
        stopped_instances = conn.stop_instances(instance_ids, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the StopInstance operation: Request would have succeeded, but DryRun flag is set')

    stopped_instances = conn.stop_instances(instance_ids)

    for instance in stopped_instances:
        instance.state.should.equal('stopping')

    with assert_raises(EC2ResponseError) as ex:
        started_instances = conn.start_instances(
            [instances[0].id], dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the StartInstance operation: Request would have succeeded, but DryRun flag is set')

    started_instances = conn.start_instances([instances[0].id])
    started_instances[0].state.should.equal('pending')


@mock_ec2_deprecated
def test_instance_reboot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    with assert_raises(EC2ResponseError) as ex:
        instance.reboot(dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the RebootInstance operation: Request would have succeeded, but DryRun flag is set')

    instance.reboot()
    instance.state.should.equal('pending')


@mock_ec2_deprecated
def test_instance_attribute_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    with assert_raises(EC2ResponseError) as ex:
        instance.modify_attribute("instanceType", "m1.small", dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifyInstanceType operation: Request would have succeeded, but DryRun flag is set')

    instance.modify_attribute("instanceType", "m1.small")

    instance_attribute = instance.get_attribute("instanceType")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get('instanceType').should.equal("m1.small")


@mock_ec2_deprecated
def test_modify_instance_attribute_security_groups():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    sg_id = conn.create_security_group('test security group', 'this is a test security group').id
    sg_id2 = conn.create_security_group('test security group 2', 'this is a test security group 2').id

    with assert_raises(EC2ResponseError) as ex:
        instance.modify_attribute("groupSet", [sg_id, sg_id2], dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set')

    instance.modify_attribute("groupSet", [sg_id, sg_id2])

    instance_attribute = instance.get_attribute("groupSet")
    instance_attribute.should.be.a(InstanceAttribute)
    group_list = instance_attribute.get('groupSet')
    any(g.id == sg_id for g in group_list).should.be.ok
    any(g.id == sg_id2 for g in group_list).should.be.ok


@mock_ec2_deprecated
def test_instance_attribute_user_data():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    with assert_raises(EC2ResponseError) as ex:
        instance.modify_attribute(
            "userData", "this is my user data", dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifyUserData operation: Request would have succeeded, but DryRun flag is set')

    instance.modify_attribute("userData", "this is my user data")

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("userData").should.equal("this is my user data")


@mock_ec2_deprecated
def test_instance_attribute_source_dest_check():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    # Default value is true
    instance.sourceDestCheck.should.equal('true')

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(True)

    # Set to false (note: Boto converts bool to string, eg 'false')

    with assert_raises(EC2ResponseError) as ex:
        instance.modify_attribute("sourceDestCheck", False, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifySourceDestCheck operation: Request would have succeeded, but DryRun flag is set')

    instance.modify_attribute("sourceDestCheck", False)

    instance.update()
    instance.sourceDestCheck.should.equal('false')

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(False)

    # Set back to true
    instance.modify_attribute("sourceDestCheck", True)

    instance.update()
    instance.sourceDestCheck.should.equal('true')

    instance_attribute = instance.get_attribute("sourceDestCheck")
    instance_attribute.should.be.a(InstanceAttribute)
    instance_attribute.get("sourceDestCheck").should.equal(True)


@mock_ec2_deprecated
def test_user_data_with_run_instance():
    user_data = b"some user data"
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', user_data=user_data)
    instance = reservation.instances[0]

    instance_attribute = instance.get_attribute("userData")
    instance_attribute.should.be.a(InstanceAttribute)
    retrieved_user_data = instance_attribute.get("userData").encode('utf-8')
    decoded_user_data = base64.decodestring(retrieved_user_data)
    decoded_user_data.should.equal(b"some user data")


@mock_ec2_deprecated
def test_run_instance_with_security_group_name():
    conn = boto.connect_ec2('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as ex:
        group = conn.create_security_group(
            'group1', "some description", dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the CreateSecurityGroup operation: Request would have succeeded, but DryRun flag is set')

    group = conn.create_security_group('group1', "some description")

    reservation = conn.run_instances('ami-1234abcd',
                                     security_groups=['group1'])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2_deprecated
def test_run_instance_with_security_group_id():
    conn = boto.connect_ec2('the_key', 'the_secret')
    group = conn.create_security_group('group1', "some description")
    reservation = conn.run_instances('ami-1234abcd',
                                     security_group_ids=[group.id])
    instance = reservation.instances[0]

    instance.groups[0].id.should.equal(group.id)
    instance.groups[0].name.should.equal("group1")


@mock_ec2_deprecated
def test_run_instance_with_instance_type():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', instance_type="t1.micro")
    instance = reservation.instances[0]

    instance.instance_type.should.equal("t1.micro")


@mock_ec2_deprecated
def test_run_instance_with_default_placement():
    conn = boto.ec2.connect_to_region("us-east-1")
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]

    instance.placement.should.equal("us-east-1a")


@mock_ec2_deprecated
def test_run_instance_with_placement():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', placement="us-east-1b")
    instance = reservation.instances[0]

    instance.placement.should.equal("us-east-1b")


@mock_ec2
def test_run_instance_with_subnet_boto3():
    client = boto3.client('ec2', region_name='eu-central-1')

    ip_networks = [
        (ipaddress.ip_network('10.0.0.0/16'), ipaddress.ip_network('10.0.99.0/24')),
        (ipaddress.ip_network('192.168.42.0/24'), ipaddress.ip_network('192.168.42.0/25'))
    ]

    # Tests instances are created with the correct IPs
    for vpc_cidr, subnet_cidr in ip_networks:
        resp = client.create_vpc(
            CidrBlock=str(vpc_cidr),
            AmazonProvidedIpv6CidrBlock=False,
            DryRun=False,
            InstanceTenancy='default'
        )
        vpc_id = resp['Vpc']['VpcId']

        resp = client.create_subnet(
            CidrBlock=str(subnet_cidr),
            VpcId=vpc_id
        )
        subnet_id = resp['Subnet']['SubnetId']

        resp = client.run_instances(
            ImageId='ami-1234abcd',
            MaxCount=1,
            MinCount=1,
            SubnetId=subnet_id
        )
        instance = resp['Instances'][0]
        instance['SubnetId'].should.equal(subnet_id)

        priv_ipv4 = ipaddress.ip_address(six.text_type(instance['PrivateIpAddress']))
        subnet_cidr.should.contain(priv_ipv4)


@mock_ec2
def test_run_instance_with_specified_private_ipv4():
    client = boto3.client('ec2', region_name='eu-central-1')

    vpc_cidr = ipaddress.ip_network('192.168.42.0/24')
    subnet_cidr = ipaddress.ip_network('192.168.42.0/25')

    resp = client.create_vpc(
        CidrBlock=str(vpc_cidr),
        AmazonProvidedIpv6CidrBlock=False,
        DryRun=False,
        InstanceTenancy='default'
    )
    vpc_id = resp['Vpc']['VpcId']

    resp = client.create_subnet(
        CidrBlock=str(subnet_cidr),
        VpcId=vpc_id
    )
    subnet_id = resp['Subnet']['SubnetId']

    resp = client.run_instances(
        ImageId='ami-1234abcd',
        MaxCount=1,
        MinCount=1,
        SubnetId=subnet_id,
        PrivateIpAddress='192.168.42.5'
    )
    instance = resp['Instances'][0]
    instance['SubnetId'].should.equal(subnet_id)
    instance['PrivateIpAddress'].should.equal('192.168.42.5')


@mock_ec2
def test_run_instance_mapped_public_ipv4():
    client = boto3.client('ec2', region_name='eu-central-1')

    vpc_cidr = ipaddress.ip_network('192.168.42.0/24')
    subnet_cidr = ipaddress.ip_network('192.168.42.0/25')

    resp = client.create_vpc(
        CidrBlock=str(vpc_cidr),
        AmazonProvidedIpv6CidrBlock=False,
        DryRun=False,
        InstanceTenancy='default'
    )
    vpc_id = resp['Vpc']['VpcId']

    resp = client.create_subnet(
        CidrBlock=str(subnet_cidr),
        VpcId=vpc_id
    )
    subnet_id = resp['Subnet']['SubnetId']
    client.modify_subnet_attribute(
        SubnetId=subnet_id,
        MapPublicIpOnLaunch={'Value': True}
    )

    resp = client.run_instances(
        ImageId='ami-1234abcd',
        MaxCount=1,
        MinCount=1,
        SubnetId=subnet_id
    )
    instance = resp['Instances'][0]
    instance.should.contain('PublicDnsName')
    instance.should.contain('PublicIpAddress')
    len(instance['PublicDnsName']).should.be.greater_than(0)
    len(instance['PublicIpAddress']).should.be.greater_than(0)


@mock_ec2_deprecated
def test_run_instance_with_nic_autocreated():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        'test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group(
        'test security group #2', 'this is a test security group')
    private_ip = "10.0.0.1"

    reservation = conn.run_instances('ami-1234abcd', subnet_id=subnet.id,
                                     security_groups=[security_group1.name],
                                     security_group_ids=[security_group2.id],
                                     private_ip_address=private_ip)
    instance = reservation.instances[0]

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)
    eni = all_enis[0]

    instance.interfaces.should.have.length_of(1)
    instance.interfaces[0].id.should.equal(eni.id)

    instance.subnet_id.should.equal(subnet.id)
    instance.groups.should.have.length_of(2)
    set([group.id for group in instance.groups]).should.equal(
        set([security_group1.id, security_group2.id]))

    eni.subnet_id.should.equal(subnet.id)
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group1.id, security_group2.id]))
    eni.private_ip_addresses.should.have.length_of(1)
    eni.private_ip_addresses[0].private_ip_address.should.equal(private_ip)


@mock_ec2_deprecated
def test_run_instance_with_nic_preexisting():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")
    security_group1 = conn.create_security_group(
        'test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group(
        'test security group #2', 'this is a test security group')
    private_ip = "54.0.0.1"
    eni = conn.create_network_interface(
        subnet.id, private_ip, groups=[security_group1.id])

    # Boto requires NetworkInterfaceCollection of NetworkInterfaceSpecifications...
    #   annoying, but generates the desired querystring.
    from boto.ec2.networkinterface import NetworkInterfaceSpecification, NetworkInterfaceCollection
    interface = NetworkInterfaceSpecification(
        network_interface_id=eni.id, device_index=0)
    interfaces = NetworkInterfaceCollection(interface)
    # end Boto objects

    reservation = conn.run_instances('ami-1234abcd', network_interfaces=interfaces,
                                     security_group_ids=[security_group2.id])
    instance = reservation.instances[0]

    instance.subnet_id.should.equal(subnet.id)

    all_enis = conn.get_all_network_interfaces()
    all_enis.should.have.length_of(1)

    instance.interfaces.should.have.length_of(1)
    instance_eni = instance.interfaces[0]
    instance_eni.id.should.equal(eni.id)

    instance_eni.subnet_id.should.equal(subnet.id)
    instance_eni.groups.should.have.length_of(2)
    set([group.id for group in instance_eni.groups]).should.equal(
        set([security_group1.id, security_group2.id]))
    instance_eni.private_ip_addresses.should.have.length_of(1)
    instance_eni.private_ip_addresses[
        0].private_ip_address.should.equal(private_ip)


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_instance_with_nic_attach_detach():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    security_group1 = conn.create_security_group(
        'test security group #1', 'this is a test security group')
    security_group2 = conn.create_security_group(
        'test security group #2', 'this is a test security group')

    reservation = conn.run_instances(
        'ami-1234abcd', security_group_ids=[security_group1.id])
    instance = reservation.instances[0]

    eni = conn.create_network_interface(subnet.id, groups=[security_group2.id])

    # Check initial instance and ENI data
    instance.interfaces.should.have.length_of(1)

    eni.groups.should.have.length_of(1)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group2.id]))

    # Attach
    with assert_raises(EC2ResponseError) as ex:
        conn.attach_network_interface(
            eni.id, instance.id, device_index=1, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the AttachNetworkInterface operation: Request would have succeeded, but DryRun flag is set')

    conn.attach_network_interface(eni.id, instance.id, device_index=1)

    # Check attached instance and ENI data
    instance.update()
    instance.interfaces.should.have.length_of(2)
    instance_eni = instance.interfaces[1]
    instance_eni.id.should.equal(eni.id)
    instance_eni.groups.should.have.length_of(2)
    set([group.id for group in instance_eni.groups]).should.equal(
        set([security_group1.id, security_group2.id]))

    eni = conn.get_all_network_interfaces(
        filters={'network-interface-id': eni.id})[0]
    eni.groups.should.have.length_of(2)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group1.id, security_group2.id]))

    # Detach
    with assert_raises(EC2ResponseError) as ex:
        conn.detach_network_interface(instance_eni.attachment.id, dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the DetachNetworkInterface operation: Request would have succeeded, but DryRun flag is set')

    conn.detach_network_interface(instance_eni.attachment.id)

    # Check detached instance and ENI data
    instance.update()
    instance.interfaces.should.have.length_of(1)

    eni = conn.get_all_network_interfaces(
        filters={'network-interface-id': eni.id})[0]
    eni.groups.should.have.length_of(1)
    set([group.id for group in eni.groups]).should.equal(
        set([security_group2.id]))

    # Detach with invalid attachment ID
    with assert_raises(EC2ResponseError) as cm:
        conn.detach_network_interface('eni-attach-1234abcd')
    cm.exception.code.should.equal('InvalidAttachmentID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_ec2_classic_has_public_ip_address():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', key_name="keypair_name")
    instance = reservation.instances[0]
    instance.ip_address.should_not.equal(None)
    instance.public_dns_name.should.contain(instance.ip_address.replace('.', '-'))
    instance.private_ip_address.should_not.equal(None)
    instance.private_dns_name.should.contain(instance.private_ip_address.replace('.', '-'))


@mock_ec2_deprecated
def test_run_instance_with_keypair():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', key_name="keypair_name")
    instance = reservation.instances[0]

    instance.key_name.should.equal("keypair_name")


@mock_ec2_deprecated
def test_describe_instance_status_no_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    all_status = conn.get_all_instance_status()
    len(all_status).should.equal(0)


@mock_ec2_deprecated
def test_describe_instance_status_with_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    conn.run_instances('ami-1234abcd', key_name="keypair_name")

    all_status = conn.get_all_instance_status()
    len(all_status).should.equal(1)
    all_status[0].instance_status.status.should.equal('ok')
    all_status[0].system_status.status.should.equal('ok')


@mock_ec2_deprecated
def test_describe_instance_status_with_instance_filter():
    conn = boto.connect_ec2('the_key', 'the_secret')

    # We want to filter based on this one
    reservation = conn.run_instances('ami-1234abcd', key_name="keypair_name")
    instance = reservation.instances[0]

    # This is just to setup the test
    conn.run_instances('ami-1234abcd', key_name="keypair_name")

    all_status = conn.get_all_instance_status(instance_ids=[instance.id])
    len(all_status).should.equal(1)
    all_status[0].id.should.equal(instance.id)

    # Call get_all_instance_status with a bad id should raise an error
    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_instance_status(instance_ids=[instance.id, "i-1234abcd"])
    cm.exception.code.should.equal('InvalidInstanceID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@requires_boto_gte("2.32.0")
@mock_ec2_deprecated
def test_describe_instance_status_with_non_running_instances():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd', min_count=3)
    instance1, instance2, instance3 = reservation.instances
    instance1.stop()
    instance2.terminate()

    all_running_status = conn.get_all_instance_status()
    all_running_status.should.have.length_of(1)
    all_running_status[0].id.should.equal(instance3.id)
    all_running_status[0].state_name.should.equal('running')

    all_status = conn.get_all_instance_status(include_all_instances=True)
    all_status.should.have.length_of(3)

    status1 = next((s for s in all_status if s.id == instance1.id), None)
    status1.state_name.should.equal('stopped')

    status2 = next((s for s in all_status if s.id == instance2.id), None)
    status2.state_name.should.equal('terminated')

    status3 = next((s for s in all_status if s.id == instance3.id), None)
    status3.state_name.should.equal('running')


@mock_ec2_deprecated
def test_get_instance_by_security_group():
    conn = boto.connect_ec2('the_key', 'the_secret')

    conn.run_instances('ami-1234abcd')
    instance = conn.get_only_instances()[0]

    security_group = conn.create_security_group('test', 'test')

    with assert_raises(EC2ResponseError) as ex:
        conn.modify_instance_attribute(instance.id, "groupSet", [
                                       security_group.id], dry_run=True)
    ex.exception.error_code.should.equal('DryRunOperation')
    ex.exception.status.should.equal(400)
    ex.exception.message.should.equal(
        'An error occurred (DryRunOperation) when calling the ModifyInstanceSecurityGroups operation: Request would have succeeded, but DryRun flag is set')

    conn.modify_instance_attribute(
        instance.id, "groupSet", [security_group.id])

    security_group_instances = security_group.instances()

    assert len(security_group_instances) == 1
    assert security_group_instances[0].id == instance.id


@mock_ec2
def test_modify_delete_on_termination():
    ec2_client = boto3.resource('ec2', region_name='us-west-1')
    result = ec2_client.create_instances(ImageId='ami-12345678', MinCount=1, MaxCount=1)
    instance = result[0]
    instance.load()
    instance.block_device_mappings[0]['Ebs']['DeleteOnTermination'].should.be(False)
    instance.modify_attribute(
        BlockDeviceMappings=[{
            'DeviceName': '/dev/sda1',
            'Ebs': {'DeleteOnTermination': True}
        }]
    )
    instance.load()
    instance.block_device_mappings[0]['Ebs']['DeleteOnTermination'].should.be(True)

@mock_ec2
def test_create_instance_ebs_optimized():
    ec2_resource = boto3.resource('ec2', region_name='eu-west-1')

    instance = ec2_resource.create_instances(
        ImageId = 'ami-12345678',
        MaxCount = 1,
        MinCount = 1,
        EbsOptimized = True,
    )[0]
    instance.load()
    instance.ebs_optimized.should.be(True)

    instance.modify_attribute(
        EbsOptimized={
            'Value': False
        }
    )
    instance.load()
    instance.ebs_optimized.should.be(False)


@mock_ec2
def test_run_multiple_instances_in_same_command():
    instance_count = 4
    client = boto3.client('ec2', region_name='us-east-1')
    client.run_instances(ImageId='ami-1234abcd',
                          MinCount=instance_count,
                          MaxCount=instance_count)
    reservations = client.describe_instances()['Reservations']

    reservations[0]['Instances'].should.have.length_of(instance_count)

    instances = reservations[0]['Instances']
    for i in range(0, instance_count):
        instances[i]['AmiLaunchIndex'].should.be(i)


@mock_ec2
def test_describe_instance_attribute():
    client = boto3.client('ec2', region_name='us-east-1')
    security_group_id = client.create_security_group(
        GroupName='test security group', Description='this is a test security group')['GroupId']
    client.run_instances(ImageId='ami-1234abcd',
                         MinCount=1,
                         MaxCount=1,
                         SecurityGroupIds=[security_group_id])
    instance_id = client.describe_instances()['Reservations'][0]['Instances'][0]['InstanceId']

    valid_instance_attributes = ['instanceType', 'kernel', 'ramdisk', 'userData', 'disableApiTermination', 'instanceInitiatedShutdownBehavior', 'rootDeviceName', 'blockDeviceMapping', 'productCodes', 'sourceDestCheck', 'groupSet', 'ebsOptimized', 'sriovNetSupport']

    for valid_instance_attribute in valid_instance_attributes:
        response = client.describe_instance_attribute(InstanceId=instance_id, Attribute=valid_instance_attribute)
        if valid_instance_attribute == "groupSet":
            response.should.have.key("Groups")
            response["Groups"].should.have.length_of(1)
            response["Groups"][0]["GroupId"].should.equal(security_group_id)
        elif valid_instance_attribute == "userData":
            response.should.have.key("UserData")
            response["UserData"].should.be.empty

    invalid_instance_attributes = ['abc', 'Kernel', 'RamDisk', 'userdata', 'iNsTaNcEtYpE']

    for invalid_instance_attribute in invalid_instance_attributes:
        with assert_raises(ClientError) as ex:
            client.describe_instance_attribute(InstanceId=instance_id, Attribute=invalid_instance_attribute)
        ex.exception.response['Error']['Code'].should.equal('InvalidParameterValue')
        ex.exception.response['ResponseMetadata']['HTTPStatusCode'].should.equal(400)
        message = 'Value ({invalid_instance_attribute}) for parameter attribute is invalid. Unknown attribute.'.format(invalid_instance_attribute=invalid_instance_attribute)
        ex.exception.response['Error']['Message'].should.equal(message)
