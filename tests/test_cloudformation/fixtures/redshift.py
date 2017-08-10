from __future__ import unicode_literals

template = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Parameters": {
        "DatabaseName": {
            "Description": "The name of the first database to be created when the cluster is created",
            "Type": "String",
            "Default": "dev",
            "AllowedPattern": "([a-z]|[0-9])+"
        },
        "ClusterType": {
            "Description": "The type of cluster",
            "Type": "String",
            "Default": "single-node",
            "AllowedValues": ["single-node", "multi-node"]
        },
        "NumberOfNodes": {
            "Description": "The number of compute nodes in the cluster. For multi-node clusters, the NumberOfNodes parameter must be greater than 1",
            "Type": "Number",
            "Default": "1"
        },
        "NodeType": {
            "Description": "The type of node to be provisioned",
            "Type": "String",
            "Default": "dw1.xlarge",
            "AllowedValues": ["dw1.xlarge", "dw1.8xlarge", "dw2.large", "dw2.8xlarge"]
        },
        "MasterUsername": {
            "Description": "The user name that is associated with the master user account for the cluster that is being created",
            "Type": "String",
            "Default": "defaultuser",
            "AllowedPattern": "([a-z])([a-z]|[0-9])*"
        },
        "MasterUserPassword":  {
            "Description": "The password that is associated with the master user account for the cluster that is being created.",
            "Type": "String",
            "NoEcho": "true"
        },
        "InboundTraffic": {
            "Description": "Allow inbound traffic to the cluster from this CIDR range.",
            "Type": "String",
            "MinLength": "9",
            "MaxLength": "18",
            "Default": "0.0.0.0/0",
            "AllowedPattern": "(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})\\.(\\d{1,3})/(\\d{1,2})",
            "ConstraintDescription": "must be a valid CIDR range of the form x.x.x.x/x."
        },
        "PortNumber": {
            "Description": "The port number on which the cluster accepts incoming connections.",
            "Type": "Number",
            "Default": "5439"
        }
    },
    "Conditions": {
        "IsMultiNodeCluster": {
            "Fn::Equals": [{"Ref": "ClusterType"}, "multi-node"]
        }
    },
    "Resources": {
        "RedshiftCluster": {
            "Type": "AWS::Redshift::Cluster",
            "DependsOn": "AttachGateway",
            "Properties": {
                "ClusterType": {"Ref": "ClusterType"},
                "NumberOfNodes": {"Fn::If": ["IsMultiNodeCluster",  {"Ref": "NumberOfNodes"}, {"Ref": "AWS::NoValue"}]},
                "NodeType": {"Ref": "NodeType"},
                "DBName": {"Ref": "DatabaseName"},
                "MasterUsername": {"Ref": "MasterUsername"},
                "MasterUserPassword": {"Ref": "MasterUserPassword"},
                "ClusterParameterGroupName": {"Ref": "RedshiftClusterParameterGroup"},
                "VpcSecurityGroupIds": [{"Ref": "SecurityGroup"}],
                "ClusterSubnetGroupName": {"Ref": "RedshiftClusterSubnetGroup"},
                "PubliclyAccessible": "true",
                "Port": {"Ref": "PortNumber"}
            }
        },
        "RedshiftClusterParameterGroup": {
            "Type": "AWS::Redshift::ClusterParameterGroup",
            "Properties": {
                "Description": "Cluster parameter group",
                "ParameterGroupFamily": "redshift-1.0",
                "Parameters": [{
                    "ParameterName": "enable_user_activity_logging",
                    "ParameterValue": "true"
                }]
            }
        },
        "RedshiftClusterSubnetGroup": {
            "Type": "AWS::Redshift::ClusterSubnetGroup",
            "Properties": {
                "Description": "Cluster subnet group",
                "SubnetIds": [{"Ref": "PublicSubnet"}]
            }
        },
        "VPC": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.0.0.0/16"
            }
        },
        "PublicSubnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "CidrBlock": "10.0.0.0/24",
                "VpcId": {"Ref": "VPC"}
            }
        },
        "SecurityGroup": {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Security group",
                "SecurityGroupIngress": [{
                    "CidrIp": {"Ref": "InboundTraffic"},
                    "FromPort": {"Ref": "PortNumber"},
                    "ToPort": {"Ref": "PortNumber"},
                    "IpProtocol": "tcp"
                }],
                "VpcId": {"Ref": "VPC"}
            }
        },
        "myInternetGateway": {
            "Type": "AWS::EC2::InternetGateway"
        },
        "AttachGateway": {
            "Type": "AWS::EC2::VPCGatewayAttachment",
            "Properties": {
                "VpcId": {"Ref": "VPC"},
                "InternetGatewayId": {"Ref": "myInternetGateway"}
            }
        },
        "PublicRouteTable": {
            "Type": "AWS::EC2::RouteTable",
            "Properties": {
                "VpcId": {
                    "Ref": "VPC"
                }
            }
        },
        "PublicRoute": {
            "Type": "AWS::EC2::Route",
            "DependsOn": "AttachGateway",
            "Properties": {
                "RouteTableId": {
                    "Ref": "PublicRouteTable"
                },
                "DestinationCidrBlock": "0.0.0.0/0",
                "GatewayId": {
                    "Ref": "myInternetGateway"
                }
            }
        },
        "PublicSubnetRouteTableAssociation": {
            "Type": "AWS::EC2::SubnetRouteTableAssociation",
            "Properties": {
                "SubnetId": {
                    "Ref": "PublicSubnet"
                },
                "RouteTableId": {
                    "Ref": "PublicRouteTable"
                }
            }
        }
    },
    "Outputs": {
        "ClusterEndpoint": {
            "Description": "Cluster endpoint",
            "Value": {"Fn::Join": [":", [{"Fn::GetAtt": ["RedshiftCluster", "Endpoint.Address"]}, {"Fn::GetAtt": ["RedshiftCluster", "Endpoint.Port"]}]]}
        },
        "ClusterName": {
            "Description": "Name of cluster",
            "Value": {"Ref": "RedshiftCluster"}
        },
        "ParameterGroupName": {
            "Description": "Name of parameter group",
            "Value": {"Ref": "RedshiftClusterParameterGroup"}
        },
        "RedshiftClusterSubnetGroupName": {
            "Description": "Name of cluster subnet group",
            "Value": {"Ref": "RedshiftClusterSubnetGroup"}
        },
        "RedshiftClusterSecurityGroupName": {
            "Description": "Name of cluster security group",
            "Value": {"Ref": "SecurityGroup"}
        }
    }
}
