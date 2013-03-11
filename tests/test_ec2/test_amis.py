import boto
from boto.exception import EC2ResponseError

import sure  # flake8: noqa

from moto import mock_ec2


@mock_ec2
def test_ami_create_and_delete():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    image = conn.create_image(instance.id, "test-ami", "this is a test ami")

    all_images = conn.get_all_images()
    all_images[0].id.should.equal(image)

    success = conn.deregister_image(image)
    success.should.be.true

    success = conn.deregister_image.when.called_with(image).should.throw(EC2ResponseError)


@mock_ec2
def test_ami_create_from_missing_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    args = ["i-abcdefg", "test-ami", "this is a test ami"]
    conn.create_image.when.called_with(*args).should.throw(EC2ResponseError)


@mock_ec2
def test_ami_pulls_attributes_from_instance():
    conn = boto.connect_ec2('the_key', 'the_secret')
    reservation = conn.run_instances('ami-1234abcd')
    instance = reservation.instances[0]
    instance.modify_attribute("kernel", "test-kernel")

    image_id = conn.create_image(instance.id, "test-ami", "this is a test ami")
    image = conn.get_image(image_id)
    image.kernel_id.should.equal('test-kernel')
