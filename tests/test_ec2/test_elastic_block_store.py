import boto
from boto.exception import EC2ResponseError

from sure import expect

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
    reservation = conn.run_instances('<ami-image-id>')
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

    conn.detach_volume.when.called_with(volume.id, instance.id, "/dev/sdh").should.throw(EC2ResponseError)
