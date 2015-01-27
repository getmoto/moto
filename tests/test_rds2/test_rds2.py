from __future__ import unicode_literals

import boto.rds2
import boto.vpc
from boto.exception import BotoServerError
import sure  # noqa

from moto import mock_ec2, mock_rds2
from tests.helpers import disable_on_py3


@disable_on_py3()
@mock_rds2
def test_create_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    database = conn.create_db_instance(db_instance_identifier='db-master-1',
                                       allocated_storage=10,
                                       engine='postgres',
                                       db_instance_class='db.m1.small',
                                       master_username='root',
                                       master_user_password='hunter2',
                                       db_security_groups=["my_sg"])
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceStatus'].should.equal('available')
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['AllocatedStorage'].should.equal('10')
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBInstanceClass'].should.equal("db.m1.small")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['MasterUsername'].should.equal("root")
    database['CreateDBInstanceResponse']['CreateDBInstanceResult']['DBInstance']['DBSecurityGroups'][0]['DBSecurityGroup']['DBSecurityGroupName'].should.equal('my_sg')


@disable_on_py3()
@mock_rds2
def test_get_databases():
    conn = boto.rds2.connect_to_region("us-west-2")

    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)

    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    conn.create_db_instance(db_instance_identifier='db-master-2',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(2)

    instances = conn.describe_db_instances("db-master-1")
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(1)
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['DBInstanceIdentifier'].should.equal("db-master-1")


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.describe_db_instances.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_db_instance():
    conn = boto.rds2.connect_to_region("us-west-2")
    database = conn.create_db_instance(db_instance_identifier='db-master-1',
                                       allocated_storage=10,
                                       engine='postgres',
                                       db_instance_class='db.m1.small',
                                       master_username='root',
                                       master_user_password='hunter2',
                                       db_security_groups=["my_sg"])
    instances = conn.describe_db_instances('db-master-1')
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['AllocatedStorage'].should.equal('10')
    conn.modify_db_instance(db_instance_identifier='db-master-1', allocated_storage=20, apply_immediately=True)
    instances = conn.describe_db_instances('db-master-1')
    instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances'][0]['AllocatedStorage'].should.equal('20')


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.modify_db_instance.when.called_with(db_instance_identifier='not-a-db',
                                             allocated_storage=20,
                                             apply_immediately=True).should.throw(BotoServerError)

@disable_on_py3()
@mock_rds2
def test_reboot_db_instance():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    database = conn.reboot_db_instance('db-master-1')
    database['RebootDBInstanceResponse']['RebootDBInstanceResult']['DBInstance']['DBInstanceIdentifier'].should.equal("db-master-1")


@disable_on_py3()
@mock_rds2
def test_reboot_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.reboot_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)
    conn.create_db_instance(db_instance_identifier='db-master-1',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"])
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(1)

    conn.delete_db_instance("db-master-1")
    instances = conn.describe_db_instances()
    list(instances['DescribeDBInstancesResponse']['DescribeDBInstancesResult']['DBInstances']).should.have.length_of(0)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    option_group = conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['OptionGroupName'].should.equal('test')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['EngineName'].should.equal('mysql')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['OptionGroupDescription'].should.equal('test option group')
    option_group['CreateOptionGroupResponse']['CreateOptionGroupResult']['OptionGroup']['MajorEngineVersion'].should.equal('5.6')


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_name():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'invalid_engine', '5.6', 'test invalid engine').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_bad_engine_major_version():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'mysql', '6.6.6', 'test invalid engine version').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_empty_description():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group.when.called_with('test', 'mysql', '5.6', '').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_create_option_group_duplicate():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    conn.create_option_group.when.called_with('test', 'mysql', '5.6', 'foo').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_describe_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_groups = conn.describe_option_groups('test')
    option_groups['DescribeOptionGroupsResponse']['DescribeOptionGroupsResult']['OptionGroupsList'][0]['OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_describe_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.describe_option_groups.when.called_with("not-a-option-group").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    option_groups = conn.describe_option_groups('test')
    option_groups['DescribeOptionGroupsResponse']['DescribeOptionGroupsResult']['OptionGroupsList'][0]['OptionGroupName'].should.equal('test')
    conn.delete_option_group('test')
    conn.describe_option_groups.when.called_with('test').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_option_group.when.called_with('non-existant').should.throw(BotoServerError)


@mock_rds2
def test_describe_option_group_options():
    conn = boto.rds2.connect_to_region("us-west-2")
    option_group_options = conn.describe_option_group_options('sqlserver-ee')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(4)
    option_group_options = conn.describe_option_group_options('sqlserver-ee', '11.00')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(2)
    option_group_options = conn.describe_option_group_options('mysql', '5.6')
    len(option_group_options['DescribeOptionGroupOptionsResponse']['DescribeOptionGroupOptionsResult']['OptionGroupOptions']).should.equal(1)
    conn.describe_option_group_options.when.called_with('non-existent').should.throw(BotoServerError)
    conn.describe_option_group_options.when.called_with('mysql', 'non-existent').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    # TODO: create option and validate before deleting.
    # if Someone can tell me how the hell to use this function
    # to add options to an option_group, I can finish coding this.
    result = conn.modify_option_group('test', [], ['MEMCACHED'], True)
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['EngineName'].should.equal('mysql')
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['Options'].should.equal([])
    result['ModifyOptionGroupResponse']['ModifyOptionGroupResult']['OptionGroupName'].should.equal('test')


@disable_on_py3()
@mock_rds2
def test_modify_option_group_no_options():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.create_option_group('test', 'mysql', '5.6', 'test option group')
    conn.modify_option_group.when.called_with('test').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_modify_non_existant_option_group():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.modify_option_group.when.called_with('non-existant', [('OptionName', 'Port', 'DBSecurityGroupMemberships', 'VpcSecurityGroupMemberships', 'OptionSettings')]).should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_delete_non_existant_database():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.delete_db_instance.when.called_with("not-a-db").should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_list_tags_invalid_arn():
    conn = boto.rds2.connect_to_region("us-west-2")
    conn.list_tags_for_resource.when.called_with('arn:aws:rds:bad-arn').should.throw(BotoServerError)


@disable_on_py3()
@mock_rds2
def test_list_tags():
    conn = boto.rds2.connect_to_region("us-west-2")
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:foo')
    result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList'].should.equal([])
    conn.create_db_instance(db_instance_identifier='db-with-tags',
                            allocated_storage=10,
                            engine='postgres',
                            db_instance_class='db.m1.small',
                            master_username='root',
                            master_user_password='hunter2',
                            db_security_groups=["my_sg"],
                            tags=[('foo', 'bar'), ('foo1', 'bar1')])
    result = conn.list_tags_for_resource('arn:aws:rds:us-west-2:1234567890:db:db-with-tags')
    result['ListTagsForResourceResponse']['ListTagsForResourceResult']['TagList'].should.equal([{'Value': 'bar',
                                                                                                 'Key': 'foo'},
                                                                                                {'Value': 'bar1',
                                                                                                 'Key': 'foo1'}])

#@disable_on_py3()
#@mock_rds2
#def test_create_database_security_group():
#    conn = boto.rds2.connect_to_region("us-west-2")
#
#    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
#    security_group.name.should.equal('db_sg')
#    security_group.description.should.equal("DB Security Group")
#    list(security_group.ip_ranges).should.equal([])
#
#
#@mock_rds2
#def test_get_security_groups():
#    conn = boto.rds2.connect_to_region("us-west-2")
#
#    list(conn.get_all_dbsecurity_groups()).should.have.length_of(0)
#
#    conn.create_dbsecurity_group('db_sg1', 'DB Security Group')
#    conn.create_dbsecurity_group('db_sg2', 'DB Security Group')
#
#    list(conn.get_all_dbsecurity_groups()).should.have.length_of(2)
#
#    databases = conn.get_all_dbsecurity_groups("db_sg1")
#    list(databases).should.have.length_of(1)
#
#    databases[0].name.should.equal("db_sg1")
#
#
#@mock_rds2
#def test_get_non_existant_security_group():
#    conn = boto.rds2.connect_to_region("us-west-2")
#    conn.get_all_dbsecurity_groups.when.called_with("not-a-sg").should.throw(BotoServerError)
#
#
#@mock_rds2
#def test_delete_database_security_group():
#    conn = boto.rds2.connect_to_region("us-west-2")
#    conn.create_dbsecurity_group('db_sg', 'DB Security Group')
#
#    list(conn.get_all_dbsecurity_groups()).should.have.length_of(1)
#
#    conn.delete_dbsecurity_group("db_sg")
#    list(conn.get_all_dbsecurity_groups()).should.have.length_of(0)
#
#
#@mock_rds2
#def test_delete_non_existant_security_group():
#    conn = boto.rds2.connect_to_region("us-west-2")
#    conn.delete_dbsecurity_group.when.called_with("not-a-db").should.throw(BotoServerError)
#
#
#@disable_on_py3()
#@mock_rds2
#def test_security_group_authorize():
#    conn = boto.rds2.connect_to_region("us-west-2")
#    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
#    list(security_group.ip_ranges).should.equal([])
#
#    security_group.authorize(cidr_ip='10.3.2.45/32')
#    security_group = conn.get_all_dbsecurity_groups()[0]
#    list(security_group.ip_ranges).should.have.length_of(1)
#    security_group.ip_ranges[0].cidr_ip.should.equal('10.3.2.45/32')
#
#
#@disable_on_py3()
#@mock_rds2
#def test_add_security_group_to_database():
#    conn = boto.rds2.connect_to_region("us-west-2")
#
#    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small', 'root', 'hunter2')
#    security_group = conn.create_dbsecurity_group('db_sg', 'DB Security Group')
#    database.modify(security_groups=[security_group])
#
#    database = conn.get_all_dbinstances()[0]
#    list(database.security_groups).should.have.length_of(1)
#
#    database.security_groups[0].name.should.equal("db_sg")
#
#
#@mock_ec2
#@mock_rds2
#def test_add_database_subnet_group():
#    vpc_conn = boto.vpc.connect_to_region("us-west-2")
#    vpc = vpc_conn.create_vpc("10.0.0.0/16")
#    subnet1 = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")
#    subnet2 = vpc_conn.create_subnet(vpc.id, "10.2.0.0/24")
#
#    subnet_ids = [subnet1.id, subnet2.id]
#    conn = boto.rds2.connect_to_region("us-west-2")
#    subnet_group = conn.create_db_subnet_group("db_subnet", "my db subnet", subnet_ids)
#    subnet_group.name.should.equal('db_subnet')
#    subnet_group.description.should.equal("my db subnet")
#    list(subnet_group.subnet_ids).should.equal(subnet_ids)
#
#
@mock_ec2
@mock_rds2
def test_describe_database_subnet_group():
   vpc_conn = boto.vpc.connect_to_region("us-west-2")
   vpc = vpc_conn.create_vpc("10.0.0.0/16")
   subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")

   conn = boto.rds2.connect_to_region("us-west-2")
   conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
   conn.create_db_subnet_group("db_subnet2", "my db subnet", [subnet.id])

   resp = conn.describe_db_subnet_groups()
   groups_resp = resp['DescribeDBSubnetGroupsResponse']

   subnet_groups = groups_resp['DescribeDBSubnetGroupsResult']['DBSubnetGroups']
   subnet_groups.should.have.length_of(2)

   subnets = groups_resp['DescribeDBSubnetGroupsResult']['DBSubnetGroups'][0]['DBSubnetGroup']['Subnets']
   subnets.should.have.length_of(1)

   list(resp).should.have.length_of(1)
   list(groups_resp).should.have.length_of(2)
   list(conn.describe_db_subnet_groups("db_subnet1")).should.have.length_of(1)

   conn.describe_db_subnet_groups.when.called_with("not-a-subnet").should.throw(BotoServerError)
#
#
#@mock_ec2
#@mock_rds2
#def test_delete_database_subnet_group():
#    vpc_conn = boto.vpc.connect_to_region("us-west-2")
#    vpc = vpc_conn.create_vpc("10.0.0.0/16")
#    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")
#
#    conn = boto.rds2.connect_to_region("us-west-2")
#    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
#    list(conn.get_all_db_subnet_groups()).should.have.length_of(1)
#
#    conn.delete_db_subnet_group("db_subnet1")
#    list(conn.get_all_db_subnet_groups()).should.have.length_of(0)
#
#    conn.delete_db_subnet_group.when.called_with("db_subnet1").should.throw(BotoServerError)
#
#
#@disable_on_py3()
#@mock_ec2
#@mock_rds2
#def test_create_database_in_subnet_group():
#    vpc_conn = boto.vpc.connect_to_region("us-west-2")
#    vpc = vpc_conn.create_vpc("10.0.0.0/16")
#    subnet = vpc_conn.create_subnet(vpc.id, "10.1.0.0/24")
#
#    conn = boto.rds2.connect_to_region("us-west-2")
#    conn.create_db_subnet_group("db_subnet1", "my db subnet", [subnet.id])
#
#    database = conn.create_dbinstance("db-master-1", 10, 'db.m1.small',
#        'root', 'hunter2', db_subnet_group_name="db_subnet1")
#
#    database = conn.get_all_dbinstances("db-master-1")[0]
#    database.subnet_group.name.should.equal("db_subnet1")
#
#
#@disable_on_py3()
#@mock_rds2
#def test_create_database_replica():
#    conn = boto.rds2.connect_to_region("us-west-2")
#
#    conn.create_db_instance(db_instance_identifier='db-master-1',
#                            allocated_storage=10,
#                            engine='postgres',
#                            db_instance_class='db.m1.small',
#                            master_username='root',
#                            master_user_password='hunter2',
#                            db_security_groups=["my_sg"])
#
#    # TODO: confirm the RESULT JSON
#    replica = conn.create_db_instance_read_replica("replica", "db-master-1", "db.m1.small")
#    print replica
    #replica.id.should.equal("replica")
    #replica.instance_class.should.equal("db.m1.small")
    #status_info = replica.status_infos[0]
    #status_info.normal.should.equal(True)
    #status_info.status_type.should.equal('read replication')
    #status_info.status.should.equal('replicating')

    # TODO: formulate checks on read replica status
#    primary = conn.describe_db_instances("db-master-1")
#    print primary
    #primary.read_replica_dbinstance_identifiers[0].should.equal("replica")

    #conn.delete_dbinstance("replica")

    #primary = conn.get_all_dbinstances("db-master-1")[0]
    #list(primary.read_replica_dbinstance_identifiers).should.have.length_of(0)
