import boto
from boto.ec2.instance import Reservation
from sure import expect

from moto import mock_ec2



@mock_ec2
def test_instance_launch_and_terminate():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('<ami-image-id>')
    reservation.should.be.a(Reservation)
    reservation.instances.should.have.length_of(1)
    instance = reservation.instances[0]

    reservations = conn.get_all_instances()
    reservations.should.have.length_of(1)
    reservations[0].id.should.equal(reservation.id)
    instances = reservations[0].instances
    instances.should.have.length_of(1)
    instances[0].id.should.equal(instance.id)
    instances[0].state.should.equal('pending')

    conn.terminate_instances(instances[0].id)

    reservations = conn.get_all_instances()
    instance = reservations[0].instances[0]
    instance.state.should.equal('shutting-down')
