from __future__ import unicode_literals
# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises  # flake8: noqa
from nose.tools import assert_raises
from moto.ec2.exceptions import EC2ClientError
from botocore.exceptions import ClientError

import boto3
import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2, mock_ec2_deprecated

SAMPLE_DOMAIN_NAME = u'example.com'
SAMPLE_NAME_SERVERS = [u'10.0.0.6', u'10.0.0.7']


@mock_ec2_deprecated
def test_vpcs():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    vpc.cidr_block.should.equal('10.0.0.0/16')

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(2)

    vpc.delete()

    all_vpcs = conn.get_all_vpcs()
    all_vpcs.should.have.length_of(1)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_vpc("vpc-1234abcd")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_vpc_defaults():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.get_all_vpcs().should.have.length_of(2)
    conn.get_all_route_tables().should.have.length_of(2)
    conn.get_all_security_groups(
        filters={'vpc-id': [vpc.id]}).should.have.length_of(1)

    vpc.delete()

    conn.get_all_vpcs().should.have.length_of(1)
    conn.get_all_route_tables().should.have.length_of(1)
    conn.get_all_security_groups(
        filters={'vpc-id': [vpc.id]}).should.have.length_of(0)


@mock_ec2_deprecated
def test_vpc_isdefault_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.get_all_vpcs(filters={'isDefault': 'true'}).should.have.length_of(1)
    vpc.delete()
    conn.get_all_vpcs(filters={'isDefault': 'true'}).should.have.length_of(1)


@mock_ec2_deprecated
def test_multiple_vpcs_default_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    conn.create_vpc("10.8.0.0/16")
    conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("192.168.0.0/16")
    conn.get_all_vpcs().should.have.length_of(4)
    vpc = conn.get_all_vpcs(filters={'isDefault': 'true'})
    vpc.should.have.length_of(1)
    vpc[0].cidr_block.should.equal('172.31.0.0/16')


@mock_ec2_deprecated
def test_vpc_state_available_filter():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.1.0.0/16")
    conn.get_all_vpcs(filters={'state': 'available'}).should.have.length_of(3)
    vpc.delete()
    conn.get_all_vpcs(filters={'state': 'available'}).should.have.length_of(2)


@mock_ec2_deprecated
def test_vpc_tagging():
    conn = boto.connect_vpc()
    vpc = conn.create_vpc("10.0.0.0/16")

    vpc.add_tag("a key", "some value")
    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the vpc
    vpc = conn.get_all_vpcs(vpc_ids=[vpc.id])[0]
    vpc.tags.should.have.length_of(1)
    vpc.tags["a key"].should.equal("some value")


@mock_ec2_deprecated
def test_vpc_get_by_id():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/16")

    vpcs = conn.get_all_vpcs(vpc_ids=[vpc1.id, vpc2.id])
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)

    with assert_raises(EC2ResponseError) as cm:
        conn.get_all_vpcs(vpc_ids=['vpc-does_not_exist'])
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2_deprecated
def test_vpc_get_by_cidr_block():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpcs = conn.get_all_vpcs(filters={'cidr': '10.0.0.0/16'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_dhcp_options_id():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(
        SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    conn.associate_dhcp_options(dhcp_options.id, vpc1.id)
    conn.associate_dhcp_options(dhcp_options.id, vpc2.id)

    vpcs = conn.get_all_vpcs(filters={'dhcp-options-id': dhcp_options.id})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Name', 'TestVPC')
    vpc3.add_tag('Name', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag:Name': 'TestVPC'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_key_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-key': 'Name'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_key_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Test', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-key': ['Name', 'Key']})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_value_superset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    vpc3 = conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')
    vpc3.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-value': 'TestVPC'})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2_deprecated
def test_vpc_get_by_tag_value_subset():
    conn = boto.connect_vpc()
    vpc1 = conn.create_vpc("10.0.0.0/16")
    vpc2 = conn.create_vpc("10.0.0.0/16")
    conn.create_vpc("10.0.0.0/24")

    vpc1.add_tag('Name', 'TestVPC')
    vpc1.add_tag('Key', 'TestVPC2')
    vpc2.add_tag('Name', 'TestVPC')
    vpc2.add_tag('Key', 'TestVPC2')

    vpcs = conn.get_all_vpcs(filters={'tag-value': ['TestVPC', 'TestVPC2']})
    vpcs.should.have.length_of(2)
    vpc_ids = tuple(map(lambda v: v.id, vpcs))
    vpc1.id.should.be.within(vpc_ids)
    vpc2.id.should.be.within(vpc_ids)


@mock_ec2
def test_default_vpc():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    default_vpc = list(ec2.vpcs.all())[0]
    default_vpc.cidr_block.should.equal('172.31.0.0/16')
    default_vpc.instance_tenancy.should.equal('default')
    default_vpc.reload()
    default_vpc.is_default.should.be.ok

    # Test default values for VPC attributes
    response = default_vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    response = default_vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').should.be.ok


@mock_ec2
def test_non_default_vpc():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC - this already exists when backend instantiated!
    #ec2.create_vpc(CidrBlock='172.31.0.0/16')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    # Test default instance_tenancy
    vpc.instance_tenancy.should.equal('default')

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').shouldnt.be.ok

    # Check Primary CIDR Block Associations
    cidr_block_association_set = next(iter(vpc.cidr_block_association_set), None)
    cidr_block_association_set['CidrBlockState']['State'].should.equal('associated')
    cidr_block_association_set['CidrBlock'].should.equal(vpc.cidr_block)
    cidr_block_association_set['AssociationId'].should.contain('vpc-cidr-assoc')


@mock_ec2
def test_vpc_dedicated_tenancy():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    # Create the non default VPC
    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16', InstanceTenancy='dedicated')
    vpc.reload()
    vpc.is_default.shouldnt.be.ok

    vpc.instance_tenancy.should.equal('dedicated')


@mock_ec2
def test_vpc_modify_enable_dns_support():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')

    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').should.be.ok

    vpc.modify_attribute(EnableDnsSupport={'Value': False})

    response = vpc.describe_attribute(Attribute='enableDnsSupport')
    attr = response.get('EnableDnsSupport')
    attr.get('Value').shouldnt.be.ok


@mock_ec2
def test_vpc_modify_enable_dns_hostnames():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Create the default VPC
    ec2.create_vpc(CidrBlock='172.31.0.0/16')

    vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
    # Test default values for VPC attributes
    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').shouldnt.be.ok

    vpc.modify_attribute(EnableDnsHostnames={'Value': True})

    response = vpc.describe_attribute(Attribute='enableDnsHostnames')
    attr = response.get('EnableDnsHostnames')
    attr.get('Value').should.be.ok


@mock_ec2_deprecated
def test_vpc_associate_dhcp_options():
    conn = boto.connect_vpc()
    dhcp_options = conn.create_dhcp_options(
        SAMPLE_DOMAIN_NAME, SAMPLE_NAME_SERVERS)
    vpc = conn.create_vpc("10.0.0.0/16")

    conn.associate_dhcp_options(dhcp_options.id, vpc.id)

    vpc.update()
    dhcp_options.id.should.equal(vpc.dhcp_options_id)


@mock_ec2
def test_associate_vpc_ipv4_cidr_block():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.10.42.0/24')

    # Associate/Extend vpc CIDR range up to 5 ciders
    for i in range(43, 47):
        response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, CidrBlock='10.10.{}.0/24'.format(i))
        response['CidrBlockAssociation']['CidrBlockState']['State'].should.equal('associating')
        response['CidrBlockAssociation']['CidrBlock'].should.equal('10.10.{}.0/24'.format(i))
        response['CidrBlockAssociation']['AssociationId'].should.contain('vpc-cidr-assoc')

    # Check all associations exist
    vpc = ec2.Vpc(vpc.id)
    vpc.cidr_block_association_set.should.have.length_of(5)
    vpc.cidr_block_association_set[2]['CidrBlockState']['State'].should.equal('associated')
    vpc.cidr_block_association_set[4]['CidrBlockState']['State'].should.equal('associated')

    # Check error on adding 6th association.
    with assert_raises(ClientError) as ex:
        response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, CidrBlock='10.10.50.0/22')
    str(ex.exception).should.equal(
        "An error occurred (CidrLimitExceeded) when calling the AssociateVpcCidrBlock "
        "operation: This network '{}' has met its maximum number of allowed CIDRs: 5".format(vpc.id))

@mock_ec2
def test_disassociate_vpc_ipv4_cidr_block():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    vpc = ec2.create_vpc(CidrBlock='10.10.42.0/24')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, CidrBlock='10.10.43.0/24')

    # Remove an extended cidr block
    vpc = ec2.Vpc(vpc.id)
    non_default_assoc_cidr_block = next(iter([x for x in vpc.cidr_block_association_set if vpc.cidr_block != x['CidrBlock']]), None)
    response = ec2.meta.client.disassociate_vpc_cidr_block(AssociationId=non_default_assoc_cidr_block['AssociationId'])
    response['CidrBlockAssociation']['CidrBlockState']['State'].should.equal('disassociating')
    response['CidrBlockAssociation']['CidrBlock'].should.equal(non_default_assoc_cidr_block['CidrBlock'])
    response['CidrBlockAssociation']['AssociationId'].should.equal(non_default_assoc_cidr_block['AssociationId'])

    # Error attempting to delete a non-existent CIDR_BLOCK association
    with assert_raises(ClientError) as ex:
        response = ec2.meta.client.disassociate_vpc_cidr_block(AssociationId='vpc-cidr-assoc-BORING123')
    str(ex.exception).should.equal(
        "An error occurred (InvalidVpcCidrBlockAssociationIdError.NotFound) when calling the "
        "DisassociateVpcCidrBlock operation: The vpc CIDR block association ID "
        "'vpc-cidr-assoc-BORING123' does not exist")

    # Error attempting to delete Primary CIDR BLOCK association
    vpc_base_cidr_assoc_id = next(iter([x for x in vpc.cidr_block_association_set
                                        if vpc.cidr_block == x['CidrBlock']]), {})['AssociationId']

    with assert_raises(ClientError) as ex:
        response = ec2.meta.client.disassociate_vpc_cidr_block(AssociationId=vpc_base_cidr_assoc_id)
    str(ex.exception).should.equal(
        "An error occurred (OperationNotPermitted) when calling the DisassociateVpcCidrBlock operation: "
        "The vpc CIDR block with association ID {} may not be disassociated. It is the primary "
        "IPv4 CIDR block of the VPC".format(vpc_base_cidr_assoc_id))

@mock_ec2
def test_cidr_block_association_filters():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    vpc1 = ec2.create_vpc(CidrBlock='10.90.0.0/16')
    vpc2 = ec2.create_vpc(CidrBlock='10.91.0.0/16')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc2.id, CidrBlock='10.10.0.0/19')
    vpc3 = ec2.create_vpc(CidrBlock='10.92.0.0/24')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock='10.92.1.0/24')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock='10.92.2.0/24')
    vpc3_assoc_response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock='10.92.3.0/24')

    # Test filters for a cidr-block in all VPCs cidr-block-associations
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'cidr-block-association.cidr-block',
                                                   'Values': ['10.10.0.0/19']}]))
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc2.id)

    # Test filter for association id in VPCs
    association_id = vpc3_assoc_response['CidrBlockAssociation']['AssociationId']
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'cidr-block-association.association-id',
                                                   'Values': [association_id]}]))
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc3.id)

    # Test filter for association state in VPC - this will never show anything in this test
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'cidr-block-association.association-id',
                                                   'Values': ['failing']}]))
    filtered_vpcs.should.be.length_of(0)

@mock_ec2
def test_vpc_associate_ipv6_cidr_block():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Test create VPC with IPV6 cidr range
    vpc = ec2.create_vpc(CidrBlock='10.10.42.0/24', AmazonProvidedIpv6CidrBlock=True)
    ipv6_cidr_block_association_set = next(iter(vpc.ipv6_cidr_block_association_set), None)
    ipv6_cidr_block_association_set['Ipv6CidrBlockState']['State'].should.equal('associated')
    ipv6_cidr_block_association_set['Ipv6CidrBlock'].should.contain('::/56')
    ipv6_cidr_block_association_set['AssociationId'].should.contain('vpc-cidr-assoc')

    # Test Fail on adding 2nd IPV6 association - AWS only allows 1 at this time!
    with assert_raises(ClientError) as ex:
        response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, AmazonProvidedIpv6CidrBlock=True)
    str(ex.exception).should.equal(
        "An error occurred (CidrLimitExceeded) when calling the AssociateVpcCidrBlock "
        "operation: This network '{}' has met its maximum number of allowed CIDRs: 1".format(vpc.id))

    # Test associate ipv6 cidr block after vpc created
    vpc = ec2.create_vpc(CidrBlock='10.10.50.0/24')
    response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc.id, AmazonProvidedIpv6CidrBlock=True)
    response['Ipv6CidrBlockAssociation']['Ipv6CidrBlockState']['State'].should.equal('associating')
    response['Ipv6CidrBlockAssociation']['Ipv6CidrBlock'].should.contain('::/56')
    response['Ipv6CidrBlockAssociation']['AssociationId'].should.contain('vpc-cidr-assoc-')

    # Check on describe vpc that has ipv6 cidr block association
    vpc = ec2.Vpc(vpc.id)
    vpc.ipv6_cidr_block_association_set.should.be.length_of(1)


@mock_ec2
def test_vpc_disassociate_ipv6_cidr_block():
    ec2 = boto3.resource('ec2', region_name='us-west-1')

    # Test create VPC with IPV6 cidr range
    vpc = ec2.create_vpc(CidrBlock='10.10.42.0/24', AmazonProvidedIpv6CidrBlock=True)
    # Test disassociating the only IPV6
    assoc_id = vpc.ipv6_cidr_block_association_set[0]['AssociationId']
    response = ec2.meta.client.disassociate_vpc_cidr_block(AssociationId=assoc_id)
    response['Ipv6CidrBlockAssociation']['Ipv6CidrBlockState']['State'].should.equal('disassociating')
    response['Ipv6CidrBlockAssociation']['Ipv6CidrBlock'].should.contain('::/56')
    response['Ipv6CidrBlockAssociation']['AssociationId'].should.equal(assoc_id)


@mock_ec2
def test_ipv6_cidr_block_association_filters():
    ec2 = boto3.resource('ec2', region_name='us-west-1')
    vpc1 = ec2.create_vpc(CidrBlock='10.90.0.0/16')

    vpc2 = ec2.create_vpc(CidrBlock='10.91.0.0/16', AmazonProvidedIpv6CidrBlock=True)
    vpc2_assoc_ipv6_assoc_id = vpc2.ipv6_cidr_block_association_set[0]['AssociationId']
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc2.id, CidrBlock='10.10.0.0/19')

    vpc3 = ec2.create_vpc(CidrBlock='10.92.0.0/24')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock='10.92.1.0/24')
    ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, CidrBlock='10.92.2.0/24')
    response = ec2.meta.client.associate_vpc_cidr_block(VpcId=vpc3.id, AmazonProvidedIpv6CidrBlock=True)
    vpc3_ipv6_cidr_block = response['Ipv6CidrBlockAssociation']['Ipv6CidrBlock']

    vpc4 = ec2.create_vpc(CidrBlock='10.95.0.0/16')  # Here for its looks

    # Test filters for an ipv6 cidr-block in all VPCs cidr-block-associations
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'ipv6-cidr-block-association.ipv6-cidr-block',
                                                   'Values': [vpc3_ipv6_cidr_block]}]))
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc3.id)

    # Test filter for association id in VPCs
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'ipv6-cidr-block-association.association-id',
                                                   'Values': [vpc2_assoc_ipv6_assoc_id]}]))
    filtered_vpcs.should.be.length_of(1)
    filtered_vpcs[0].id.should.equal(vpc2.id)

    # Test filter for association state in VPC - this will never show anything in this test
    filtered_vpcs = list(ec2.vpcs.filter(Filters=[{'Name': 'ipv6-cidr-block-association.state',
                                                   'Values': ['associated']}]))
    filtered_vpcs.should.be.length_of(2)   # 2 of 4 VPCs
