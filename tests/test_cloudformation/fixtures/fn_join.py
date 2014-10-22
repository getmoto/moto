from __future__ import unicode_literals

template = {
    "Resources": {
        "EC2EIP": {
            "Type": "AWS::EC2::EIP"
        }
    },
    "Outputs": {
        "EIP": {
            "Description": "EIP for joining",
            "Value": {
                "Fn::Join": [
                    ":",
                    [
                        "test eip",
                        {"Ref": "EC2EIP"}
                    ]
                ]
            }
        }
    }
}
