from moto.core import get_account_id, CloudFormationModel
from ..exceptions import InvalidNetworkAttachmentIdError, InvalidNetworkInterfaceIdError
from .core import TaggedEC2Resource
from .security_groups import SecurityGroup
from ..utils import (
    random_eni_id,
    generate_dns_from_ip,
    random_mac_address,
    random_private_ip,
    random_public_ip,
    generic_filter,
)


class NetworkInterface(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        subnet,
        private_ip_address,
        private_ip_addresses=None,
        device_index=0,
        public_ip_auto_assign=False,
        group_ids=None,
        description=None,
        tags=None,
        **kwargs,
    ):
        self.ec2_backend = ec2_backend
        self.id = random_eni_id()
        self.device_index = device_index
        if isinstance(private_ip_address, list) and private_ip_address:
            private_ip_address = private_ip_address[0]
        self.private_ip_address = private_ip_address or None
        self.private_ip_addresses = private_ip_addresses or []
        self.ipv6_addresses = kwargs.get("ipv6_addresses") or []

        self.subnet = subnet
        if isinstance(subnet, str):
            self.subnet = self.ec2_backend.get_subnet(subnet)
        self.instance = None
        self.attachment_id = None
        self.attach_time = None
        self.delete_on_termination = False
        self.description = description
        self.source_dest_check = True

        self.public_ip = None
        self.public_ip_auto_assign = public_ip_auto_assign
        self.start()
        self.add_tags(tags or {})
        self.status = "available"
        self.mac_address = random_mac_address()
        self.interface_type = "interface"
        # Local set to the ENI. When attached to an instance, @property group_set
        #   returns groups for both self and the attached instance.
        self._group_set = []

        if self.subnet.ipv6_cidr_block_associations:
            association = list(self.subnet.ipv6_cidr_block_associations.values())[0]
            subnet_ipv6_cidr_block = association.get("ipv6CidrBlock")
            if kwargs.get("ipv6_address_count"):
                while len(self.ipv6_addresses) < kwargs.get("ipv6_address_count"):
                    ip = random_private_ip(subnet_ipv6_cidr_block, ipv6=True)
                    if ip not in self.ipv6_addresses:
                        self.ipv6_addresses.append(ip)

        if self.private_ip_addresses:
            primary_selected = True if private_ip_address else False
            for item in self.private_ip_addresses.copy():
                if isinstance(item, str):
                    self.private_ip_addresses.remove(item)
                    self.private_ip_addresses.append(
                        {
                            "Primary": True if not primary_selected else False,
                            "PrivateIpAddress": item,
                        }
                    )
                    primary_selected = True

        if not self.private_ip_address:
            if self.private_ip_addresses:
                for ip in self.private_ip_addresses:
                    if isinstance(ip, dict) and ip.get("Primary"):
                        self.private_ip_address = ip.get("PrivateIpAddress")
                        break
            if not self.private_ip_addresses:
                self.private_ip_address = random_private_ip(self.subnet.cidr_block)

        if not self.private_ip_addresses:
            self.private_ip_addresses.append(
                {"Primary": True, "PrivateIpAddress": self.private_ip_address}
            )

        secondary_ips = kwargs.get("secondary_ips_count", None)
        if secondary_ips:
            ips = [
                random_private_ip(self.subnet.cidr_block)
                for index in range(0, int(secondary_ips))
            ]
            if ips:
                self.private_ip_addresses.extend(
                    [{"Primary": False, "PrivateIpAddress": ip} for ip in ips]
                )

        if self.subnet:
            vpc = self.ec2_backend.get_vpc(self.subnet.vpc_id)
            if vpc and vpc.enable_dns_hostnames:
                self.private_dns_name = generate_dns_from_ip(self.private_ip_address)
                for address in self.private_ip_addresses:
                    if address.get("Primary", None):
                        address["PrivateDnsName"] = self.private_dns_name

        group = None
        if group_ids:
            for group_id in group_ids:
                group = self.ec2_backend.get_security_group_from_id(group_id)
                if not group:
                    # Create with specific group ID.
                    group = SecurityGroup(
                        self.ec2_backend,
                        group_id,
                        group_id,
                        group_id,
                        vpc_id=subnet.vpc_id,
                    )
                    self.ec2_backend.groups[subnet.vpc_id][group_id] = group
                if group:
                    self._group_set.append(group)
        if not group_ids:
            group = self.ec2_backend.get_default_security_group(vpc.id)
            if group:
                self._group_set.append(group)

    @property
    def owner_id(self):
        return get_account_id()

    @property
    def association(self):
        association = {}
        if self.public_ip:
            eips = self.ec2_backend.address_by_ip(
                [self.public_ip], fail_if_not_found=False
            )
            eip = eips[0] if len(eips) > 0 else None
            if eip:
                association["allocationId"] = eip.allocation_id or None
                association["associationId"] = eip.association_id or None
        return association

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-networkinterface.html
        return "AWS::EC2::NetworkInterface"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        security_group_ids = properties.get("SecurityGroups", [])

        ec2_backend = ec2_backends[region_name]
        subnet_id = properties.get("SubnetId")
        if subnet_id:
            subnet = ec2_backend.get_subnet(subnet_id)
        else:
            subnet = None

        private_ip_address = properties.get("PrivateIpAddress", None)
        description = properties.get("Description", None)

        network_interface = ec2_backend.create_network_interface(
            subnet,
            private_ip_address,
            group_ids=security_group_ids,
            description=description,
        )
        return network_interface

    def stop(self):
        if self.public_ip_auto_assign:
            self.public_ip = None

    def start(self):
        self.check_auto_public_ip()

    def check_auto_public_ip(self):
        if (
            self.public_ip_auto_assign
            and str(self.public_ip_auto_assign).lower() == "true"
        ):
            self.public_ip = random_public_ip()

    @property
    def group_set(self):
        if self.instance and self.instance.security_groups:
            return set(self._group_set) | set(self.instance.security_groups)
        else:
            return self._group_set

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in ["PrimaryPrivateIpAddress", "SecondaryPrivateIpAddresses"]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "PrimaryPrivateIpAddress":
            return self.private_ip_address
        elif attribute_name == "SecondaryPrivateIpAddresses":
            raise NotImplementedError(
                '"Fn::GetAtt" : [ "{0}" , "SecondaryPrivateIpAddresses" ]"'
            )
        raise UnformattedGetAttTemplateException()

    @property
    def physical_resource_id(self):
        return self.id

    def get_filter_value(self, filter_name):
        if filter_name == "network-interface-id":
            return self.id
        elif filter_name in ("addresses.private-ip-address", "private-ip-address"):
            return self.private_ip_address
        elif filter_name == "subnet-id":
            return self.subnet.id
        elif filter_name == "vpc-id":
            return self.subnet.vpc_id
        elif filter_name == "group-id":
            return [group.id for group in self._group_set]
        elif filter_name == "availability-zone":
            return self.subnet.availability_zone
        elif filter_name == "description":
            return self.description
        elif filter_name == "attachment.instance-id":
            return self.instance.id if self.instance else None
        elif filter_name == "attachment.instance-owner-id":
            return self.owner_id
        else:
            return super().get_filter_value(filter_name, "DescribeNetworkInterfaces")


class NetworkInterfaceBackend:
    def __init__(self):
        self.enis = {}

    def create_network_interface(
        self,
        subnet,
        private_ip_address,
        private_ip_addresses=None,
        group_ids=None,
        description=None,
        tags=None,
        **kwargs,
    ):
        eni = NetworkInterface(
            self,
            subnet,
            private_ip_address,
            private_ip_addresses,
            group_ids=group_ids,
            description=description,
            tags=tags,
            **kwargs,
        )
        self.enis[eni.id] = eni
        return eni

    def get_network_interface(self, eni_id):
        for eni in self.enis.values():
            if eni_id == eni.id:
                return eni
        raise InvalidNetworkInterfaceIdError(eni_id)

    def delete_network_interface(self, eni_id):
        deleted = self.enis.pop(eni_id, None)
        if not deleted:
            raise InvalidNetworkInterfaceIdError(eni_id)
        return deleted

    def describe_network_interfaces(self, filters=None):
        # Note: This is only used in EC2Backend#do_resources_exist
        # Client-calls use #get_all_network_interfaces()
        # We should probably merge these at some point..
        enis = self.enis.values()

        if filters:
            for (_filter, _filter_value) in filters.items():
                if _filter == "network-interface-id":
                    _filter = "id"
                    enis = [
                        eni for eni in enis if getattr(eni, _filter) in _filter_value
                    ]
                else:
                    self.raise_not_implemented_error(
                        "The filter '{0}' for DescribeNetworkInterfaces".format(_filter)
                    )
        return enis

    def attach_network_interface(self, eni_id, instance_id, device_index):
        eni = self.get_network_interface(eni_id)
        instance = self.get_instance(instance_id)
        return instance.attach_eni(eni, device_index)

    def detach_network_interface(self, attachment_id):
        found_eni = None

        for eni in self.enis.values():
            if eni.attachment_id == attachment_id:
                found_eni = eni
                break
        else:
            raise InvalidNetworkAttachmentIdError(attachment_id)

        found_eni.instance.detach_eni(found_eni)

    def modify_network_interface_attribute(
        self, eni_id, group_ids, source_dest_check=None, description=None
    ):
        eni = self.get_network_interface(eni_id)
        groups = [self.get_security_group_from_id(group_id) for group_id in group_ids]
        if groups:
            eni._group_set = groups
        if source_dest_check in [True, False]:
            eni.source_dest_check = source_dest_check

        if description:
            eni.description = description

    def get_all_network_interfaces(self, eni_ids=None, filters=None):
        enis = self.enis.copy().values()

        if eni_ids:
            enis = [eni for eni in enis if eni.id in eni_ids]
            if len(enis) != len(eni_ids):
                invalid_id = list(
                    set(eni_ids).difference(set([eni.id for eni in enis]))
                )[0]
                raise InvalidNetworkInterfaceIdError(invalid_id)

        return generic_filter(filters, enis)

    def unassign_private_ip_addresses(self, eni_id=None, private_ip_address=None):
        eni = self.get_network_interface(eni_id)
        if private_ip_address:
            for item in eni.private_ip_addresses.copy():
                if item.get("PrivateIpAddress") in private_ip_address:
                    eni.private_ip_addresses.remove(item)
        return eni

    def assign_private_ip_addresses(self, eni_id=None, secondary_ips_count=None):
        eni = self.get_network_interface(eni_id)
        eni_assigned_ips = [
            item.get("PrivateIpAddress") for item in eni.private_ip_addresses
        ]
        while secondary_ips_count:
            ip = random_private_ip(eni.subnet.cidr_block)
            if ip not in eni_assigned_ips:
                eni.private_ip_addresses.append(
                    {"Primary": False, "PrivateIpAddress": ip}
                )
                secondary_ips_count -= 1
        return eni

    def assign_ipv6_addresses(self, eni_id=None, ipv6_addresses=None, ipv6_count=None):
        eni = self.get_network_interface(eni_id)
        if ipv6_addresses:
            eni.ipv6_addresses.extend(ipv6_addresses)

        while ipv6_count:
            association = list(eni.subnet.ipv6_cidr_block_associations.values())[0]
            subnet_ipv6_cidr_block = association.get("ipv6CidrBlock")
            ip = random_private_ip(subnet_ipv6_cidr_block, ipv6=True)
            if ip not in eni.ipv6_addresses:
                eni.ipv6_addresses.append(ip)
                ipv6_count -= 1
        return eni

    def unassign_ipv6_addresses(self, eni_id=None, ips=None):
        eni = self.get_network_interface(eni_id)
        if ips:
            for ip in eni.ipv6_addresses.copy():
                if ip in ips:
                    eni.ipv6_addresses.remove(ip)
        return eni, ips
