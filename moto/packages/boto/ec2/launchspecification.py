# Copyright (c) 2006-2012 Mitch Garnaat http://garnaat.org/
# Copyright (c) 2012 Amazon.com, Inc. or its affiliates.  All Rights Reserved
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Represents a launch specification for Spot instances.
"""

from moto.packages.boto.ec2.ec2object import EC2Object


class LaunchSpecification(EC2Object):
    def __init__(self, connection=None):
        super(LaunchSpecification, self).__init__(connection)
        self.key_name = None
        self.instance_type = None
        self.image_id = None
        self.groups = []
        self.placement = None
        self.kernel = None
        self.ramdisk = None
        self.monitored = False
        self.subnet_id = None
        self._in_monitoring_element = False
        self.block_device_mapping = None
        self.instance_profile = None
        self.ebs_optimized = False

    def __repr__(self):
        return "LaunchSpecification(%s)" % self.image_id
