import boto.ec2
import sure
from moto import mock_ec2


def add_servers_to_region(ami_id, count, region):
    conn = boto.ec2.connect_to_region(region)
    for index in range(count):
        conn.run_instances(ami_id)


@mock_ec2
def test_add_servers_to_a_single_region():
    region = 'ap-northeast-1'
    add_servers_to_region('ami-1234abcd', 1, region)
    add_servers_to_region('ami-5678efgh', 1, region)

    conn = boto.ec2.connect_to_region(region)
    instances = conn.get_only_instances()
    len(instances).should.equal(2)
    instances.sort(key=lambda x: x.image_id)
    
    instances[0].image_id.should.equal('ami-1234abcd')
    instances[1].image_id.should.equal('ami-5678efgh')


@mock_ec2
def test_add_servers_to_multiple_regions():
    region1 = 'us-east-1'
    region2 = 'ap-northeast-1'
    add_servers_to_region('ami-1234abcd', 1, region1)
    add_servers_to_region('ami-5678efgh', 1, region2)

    us_conn = boto.ec2.connect_to_region(region1)
    ap_conn = boto.ec2.connect_to_region(region2)
    us_instances = us_conn.get_only_instances()
    ap_instances = ap_conn.get_only_instances()

    len(us_instances).should.equal(1)
    len(ap_instances).should.equal(1)
    
    us_instances[0].image_id.should.equal('ami-1234abcd')
    ap_instances[0].image_id.should.equal('ami-5678efgh')

