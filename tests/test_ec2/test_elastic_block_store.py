import boto
from boto.exception import EC2ResponseError
import sure  # flake8: noqa

from moto import mock_ec2


@mock_ec2
def test_create_and_delete_volume():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    all_volumes = conn.get_all_volumes()
    all_volumes.should.have.length_of(1)
    all_volumes[0].size.should.equal(80)
    all_volumes[0].zone.should.equal("us-east-1a")

    volume = all_volumes[0]
    volume.delete()

    conn.get_all_volumes().should.have.length_of(0)

    # Deleting something that was already deleted should throw an error
    volume.delete.when.called_with().should.throw(EC2ResponseError)


@mock_ec2
def test_volume_attach_and_detach():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    volume = conn.create_volume(80, "us-east-1a")

    volume.update()
    volume.volume_state().should.equal('available')

    volume.attach(instance.id, "/dev/sdh")

    volume.update()
    volume.volume_state().should.equal('in-use')

    volume.attach_data.instance_id.should.equal(instance.id)

    volume.detach()

    volume.update()
    volume.volume_state().should.equal('available')

    volume.attach.when.called_with(
        'i-1234abcd', "/dev/sdh").should.throw(EC2ResponseError)

    conn.detach_volume.when.called_with(
        volume.id, instance.id, "/dev/sdh").should.throw(EC2ResponseError)

    conn.detach_volume.when.called_with(
        volume.id, 'i-1234abcd', "/dev/sdh").should.throw(EC2ResponseError)


@mock_ec2
def test_create_snapshot():
    conn = boto.connect_ec2('the_key', 'the_secret')
    volume = conn.create_volume(80, "us-east-1a")

    volume.create_snapshot('a test snapshot')

    snapshots = conn.get_all_snapshots()
    snapshots.should.have.length_of(1)
    snapshots[0].description.should.equal('a test snapshot')

    # Create snapshot without description
    snapshot = volume.create_snapshot()
    conn.get_all_snapshots().should.have.length_of(2)

    snapshot.delete()
    conn.get_all_snapshots().should.have.length_of(1)

    # Deleting something that was already deleted should throw an error
    snapshot.delete.when.called_with().should.throw(EC2ResponseError)
