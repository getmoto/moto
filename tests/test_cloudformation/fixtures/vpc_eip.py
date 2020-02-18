from __future__ import unicode_literals

template = {
    "Resources": {"VPCEIP": {"Type": "AWS::EC2::EIP", "Properties": {"Domain": "vpc"}}}
}
