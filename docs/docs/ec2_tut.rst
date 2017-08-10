.. _ec2_tut:

=======================
Use Moto as EC2 backend
=======================

This tutorial explains ``moto.ec2``'s features and how to use it. This
tutorial assumes that you have already downloaded and installed boto and moto.
Before all code examples the following snippet is launched::

    >>> import boto.ec2, moto
    >>> mock_ec2 = moto.mock_ec2()
    >>> mock_ec2.start()
    >>> conn = boto.ec2.connect_to_region("eu-west-1")

Launching instances
-------------------

After mock is started, the behavior is the same than previously::

    >>> reservation = conn.run_instances('ami-f00ba4')
    >>> reservation.instances[0]
    Instance:i-91dd2f32

Moto set static or generate random object's attributes::

    >>> vars(reservation.instances[0])
    {'_in_monitoring_element': False,
     '_placement': None,
     '_previous_state': None,
     '_state': pending(0),
     'ami_launch_index': u'0',
     'architecture': u'x86_64',
     'block_device_mapping': None,
     'client_token': '',
     'connection': EC2Connection:ec2.eu-west-1.amazonaws.com,
     'dns_name': u'ec2-54.214.135.84.compute-1.amazonaws.com',
     'ebs_optimized': False,
     'eventsSet': None,
     'group_name': None,
     'groups': [],
     'hypervisor': u'xen',
     'id': u'i-91dd2f32',
     'image_id': u'f00ba4',
     'instance_profile': None,
     'instance_type': u'm1.small',
     'interfaces': [NetworkInterface:eni-ed65f870],
     'ip_address': u'54.214.135.84',
     'item': u'\n        ',
     'kernel': u'None',
     'key_name': u'None',
     'launch_time': u'2015-07-27T05:59:57Z',
     'monitored': True,
     'monitoring': u'\n          ',
     'monitoring_state': u'enabled',
     'persistent': False,
     'platform': None,
     'private_dns_name': u'ip-10.136.187.180.ec2.internal',
     'private_ip_address': u'10.136.187.180',
     'product_codes': [],
     'public_dns_name': u'ec2-54.214.135.84.compute-1.amazonaws.com',
     'ramdisk': None,
     'reason': '',
     'region': RegionInfo:eu-west-1,
     'requester_id': None,
     'root_device_name': None,
     'root_device_type': None,
     'sourceDestCheck': u'true',
     'spot_instance_request_id': None,
     'state_reason': None,
     'subnet_id': None,
     'tags': {},
     'virtualization_type': u'paravirtual',
     'vpc_id': None}
