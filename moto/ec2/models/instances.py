import copy
import warnings
from collections import OrderedDict
from datetime import datetime
from moto import settings

from moto.core import get_account_id
from moto.core import CloudFormationModel
from moto.core.utils import camelcase_to_underscores
from moto.ec2.models.instance_types import (
    INSTANCE_TYPE_OFFERINGS,
    InstanceTypeOfferingBackend,
)
from moto.packages.boto.ec2.blockdevicemapping import BlockDeviceMapping
from moto.packages.boto.ec2.instance import Instance as BotoInstance
from moto.packages.boto.ec2.instance import Reservation

from ..exceptions import (
    AvailabilityZoneNotFromRegionError,
    EC2ClientError,
    InvalidInstanceIdError,
    InvalidInstanceTypeError,
    InvalidParameterValueErrorUnknownAttribute,
    OperationNotPermitted4,
)
from ..utils import (
    convert_tag_spec,
    filter_reservations,
    random_eni_attach_id,
    random_instance_id,
    random_private_ip,
    random_reservation_id,
    utc_date_and_time,
)
from .core import TaggedEC2Resource


class InstanceState(object):
    def __init__(self, name="pending", code=0):
        self.name = name
        self.code = code


class StateReason(object):
    def __init__(self, message="", code=""):
        self.message = message
        self.code = code


class Instance(TaggedEC2Resource, BotoInstance, CloudFormationModel):
    VALID_ATTRIBUTES = {
        "instanceType",
        "kernel",
        "ramdisk",
        "userData",
        "disableApiTermination",
        "instanceInitiatedShutdownBehavior",
        "rootDeviceName",
        "blockDeviceMapping",
        "productCodes",
        "sourceDestCheck",
        "groupSet",
        "ebsOptimized",
        "sriovNetSupport",
    }

    def __init__(self, ec2_backend, image_id, user_data, security_groups, **kwargs):
        super().__init__()
        self.ec2_backend = ec2_backend
        self.id = random_instance_id()
        self.owner_id = get_account_id()
        self.lifecycle = kwargs.get("lifecycle")

        nics = kwargs.get("nics", {})

        launch_template_arg = kwargs.get("launch_template", {})
        if launch_template_arg and not image_id:
            # the image id from the template should be used
            template_version = ec2_backend._get_template_from_args(launch_template_arg)
            self.image_id = template_version.image_id
        else:
            self.image_id = image_id
        # Check if we have tags to process
        if launch_template_arg:
            template_version = ec2_backend._get_template_from_args(launch_template_arg)
            tag_spec_set = template_version.data.get("TagSpecification", {})
            tags = convert_tag_spec(tag_spec_set)
            instance_tags = tags.get("instance", {})
            self.add_tags(instance_tags)

        self._state = InstanceState("running", 16)
        self._reason = ""
        self._state_reason = StateReason()
        self.user_data = user_data
        self.security_groups = security_groups
        self.instance_type = kwargs.get("instance_type", "m1.small")
        self.region_name = kwargs.get("region_name", "us-east-1")
        placement = kwargs.get("placement", None)
        self.subnet_id = kwargs.get("subnet_id")
        if not self.subnet_id:
            self.subnet_id = next(
                (n["SubnetId"] for n in nics if "SubnetId" in n), None
            )
        in_ec2_classic = not bool(self.subnet_id)
        self.key_name = kwargs.get("key_name")
        self.ebs_optimized = kwargs.get("ebs_optimized", False)
        self.source_dest_check = "true"
        self.launch_time = utc_date_and_time()
        self.ami_launch_index = kwargs.get("ami_launch_index", 0)
        self.disable_api_termination = kwargs.get("disable_api_termination", False)
        self.instance_initiated_shutdown_behavior = (
            kwargs.get("instance_initiated_shutdown_behavior") or "stop"
        )
        self.sriov_net_support = "simple"
        self._spot_fleet_id = kwargs.get("spot_fleet_id", None)
        self.associate_public_ip = kwargs.get("associate_public_ip", False)
        if in_ec2_classic:
            # If we are in EC2-Classic, autoassign a public IP
            self.associate_public_ip = True

        amis = self.ec2_backend.describe_images(filters={"image-id": self.image_id})
        ami = amis[0] if amis else None
        if ami is None:
            warnings.warn(
                "Could not find AMI with image-id:{0}, "
                "in the near future this will "
                "cause an error.\n"
                "Use ec2_backend.describe_images() to "
                "find suitable image for your test".format(self.image_id),
                PendingDeprecationWarning,
            )

        self.platform = ami.platform if ami else None
        self.virtualization_type = ami.virtualization_type if ami else "paravirtual"
        self.architecture = ami.architecture if ami else "x86_64"
        self.root_device_name = ami.root_device_name if ami else None

        # handle weird bug around user_data -- something grabs the repr(), so
        # it must be clean
        if isinstance(self.user_data, list) and len(self.user_data) > 0:
            if isinstance(self.user_data[0], bytes):
                # string will have a "b" prefix -- need to get rid of it
                self.user_data[0] = self.user_data[0].decode("utf-8")

        if self.subnet_id:
            subnet = ec2_backend.get_subnet(self.subnet_id)
            self._placement.zone = subnet.availability_zone

            if self.associate_public_ip is None:
                # Mapping public ip hasnt been explicitly enabled or disabled
                self.associate_public_ip = subnet.map_public_ip_on_launch == "true"
        elif placement:
            self._placement.zone = placement
        else:
            self._placement.zone = ec2_backend.region_name + "a"

        self.block_device_mapping = BlockDeviceMapping()

        self._private_ips = set()
        self.prep_nics(
            nics,
            private_ip=kwargs.get("private_ip"),
            associate_public_ip=self.associate_public_ip,
            security_groups=self.security_groups,
        )

    @property
    def vpc_id(self):
        if self.subnet_id:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            return subnet.vpc_id
        if self.nics and 0 in self.nics:
            return self.nics[0].subnet.vpc_id
        return None

    def __del__(self):
        try:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            for ip in self._private_ips:
                subnet.del_subnet_ip(ip)
        except Exception:
            # Its not "super" critical we clean this up, as reset will do this
            # worst case we'll get IP address exaustion... rarely
            pass

    def add_block_device(
        self,
        size,
        device_path,
        snapshot_id=None,
        encrypted=False,
        delete_on_termination=False,
        kms_key_id=None,
        volume_type=None,
    ):
        volume = self.ec2_backend.create_volume(
            size=size,
            zone_name=self._placement.zone,
            snapshot_id=snapshot_id,
            encrypted=encrypted,
            kms_key_id=kms_key_id,
            volume_type=volume_type,
        )
        self.ec2_backend.attach_volume(
            volume.id, self.id, device_path, delete_on_termination
        )

    def setup_defaults(self):
        # Default have an instance with root volume should you not wish to
        # override with attach volume cmd.
        volume = self.ec2_backend.create_volume(size=8, zone_name=self._placement.zone)
        self.ec2_backend.attach_volume(volume.id, self.id, "/dev/sda1", True)

    def teardown_defaults(self):
        for device_path in list(self.block_device_mapping.keys()):
            volume = self.block_device_mapping[device_path]
            volume_id = volume.volume_id
            self.ec2_backend.detach_volume(volume_id, self.id, device_path)
            if volume.delete_on_termination:
                self.ec2_backend.delete_volume(volume_id)

    @property
    def get_block_device_mapping(self):
        return self.block_device_mapping.items()

    @property
    def private_ip(self):
        return self.nics[0].private_ip_address

    @property
    def private_dns(self):
        formatted_ip = self.private_ip.replace(".", "-")
        if self.region_name == "us-east-1":
            return "ip-{0}.ec2.internal".format(formatted_ip)
        else:
            return "ip-{0}.{1}.compute.internal".format(formatted_ip, self.region_name)

    @property
    def public_ip(self):
        return self.nics[0].public_ip

    @property
    def public_dns(self):
        if self.public_ip:
            formatted_ip = self.public_ip.replace(".", "-")
            if self.region_name == "us-east-1":
                return "ec2-{0}.compute-1.amazonaws.com".format(formatted_ip)
            else:
                return "ec2-{0}.{1}.compute.amazonaws.com".format(
                    formatted_ip, self.region_name
                )

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-instance.html
        return "AWS::EC2::Instance"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        security_group_ids = properties.get("SecurityGroups", [])
        group_names = [
            ec2_backend.get_security_group_from_id(group_id).name
            for group_id in security_group_ids
        ]

        reservation = ec2_backend.add_instances(
            image_id=properties["ImageId"],
            user_data=properties.get("UserData"),
            count=1,
            security_group_names=group_names,
            instance_type=properties.get("InstanceType", "m1.small"),
            is_instance_type_default=not properties.get("InstanceType"),
            subnet_id=properties.get("SubnetId"),
            key_name=properties.get("KeyName"),
            private_ip=properties.get("PrivateIpAddress"),
            block_device_mappings=properties.get("BlockDeviceMappings", {}),
        )
        instance = reservation.instances[0]
        for tag in properties.get("Tags", []):
            instance.add_tag(tag["Key"], tag["Value"])

        # Associating iam instance profile.
        # TODO: Don't forget to implement replace_iam_instance_profile_association once update_from_cloudformation_json
        #  for ec2 instance will be implemented.
        if properties.get("IamInstanceProfile"):
            ec2_backend.associate_iam_instance_profile(
                instance_id=instance.id,
                iam_instance_profile_name=properties.get("IamInstanceProfile"),
            )

        return instance

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        from ..models import ec2_backends

        ec2_backend = ec2_backends[region_name]
        all_instances = ec2_backend.all_instances()

        # the resource_name for instances is the stack name, logical id, and random suffix separated
        # by hyphens.  So to lookup the instances using the 'aws:cloudformation:logical-id' tag, we need to
        # extract the logical-id from the resource_name
        logical_id = resource_name.split("-")[1]

        for instance in all_instances:
            instance_tags = instance.get_tags()
            for tag in instance_tags:
                if (
                    tag["key"] == "aws:cloudformation:logical-id"
                    and tag["value"] == logical_id
                ):
                    instance.delete(region_name)

    @property
    def physical_resource_id(self):
        return self.id

    def start(self):
        for nic in self.nics.values():
            nic.start()

        self._state.name = "running"
        self._state.code = 16

        self._reason = ""
        self._state_reason = StateReason()

    def stop(self):
        for nic in self.nics.values():
            nic.stop()

        self._state.name = "stopped"
        self._state.code = 80

        self._reason = "User initiated ({0})".format(
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        self._state_reason = StateReason(
            "Client.UserInitiatedShutdown: User initiated shutdown",
            "Client.UserInitiatedShutdown",
        )

    def is_running(self):
        return self._state.name == "running"

    def delete(self, region):  # pylint: disable=unused-argument
        self.terminate()

    def terminate(self):
        for nic in self.nics.values():
            nic.stop()

        self.teardown_defaults()

        if self._spot_fleet_id:
            spot_fleet = self.ec2_backend.get_spot_fleet_request(self._spot_fleet_id)
            for spec in spot_fleet.launch_specs:
                if (
                    spec.instance_type == self.instance_type
                    and spec.subnet_id == self.subnet_id
                ):
                    break
            spot_fleet.fulfilled_capacity -= spec.weighted_capacity
            spot_fleet.spot_requests = [
                req for req in spot_fleet.spot_requests if req.instance != self
            ]

        self._state.name = "terminated"
        self._state.code = 48

        self._reason = "User initiated ({0})".format(
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        self._state_reason = StateReason(
            "Client.UserInitiatedShutdown: User initiated shutdown",
            "Client.UserInitiatedShutdown",
        )

        # Disassociate iam instance profile if associated, otherwise iam_instance_profile_associations will
        # be pointing to None.
        if self.ec2_backend.iam_instance_profile_associations.get(self.id):
            self.ec2_backend.disassociate_iam_instance_profile(
                association_id=self.ec2_backend.iam_instance_profile_associations[
                    self.id
                ].id
            )

    def reboot(self):
        self._state.name = "running"
        self._state.code = 16

        self._reason = ""
        self._state_reason = StateReason()

    @property
    def dynamic_group_list(self):
        return self.security_groups

    def prep_nics(
        self, nic_spec, private_ip=None, associate_public_ip=None, security_groups=None
    ):
        self.nics = {}

        if self.subnet_id:
            subnet = self.ec2_backend.get_subnet(self.subnet_id)
            if not private_ip:
                private_ip = subnet.get_available_subnet_ip(instance=self)
            else:
                subnet.request_ip(private_ip, instance=self)

            self._private_ips.add(private_ip)
        elif private_ip is None:
            # Preserve old behaviour if in EC2-Classic mode
            private_ip = random_private_ip()

        # Primary NIC defaults
        primary_nic = {
            "SubnetId": self.subnet_id,
            "PrivateIpAddress": private_ip,
            "AssociatePublicIpAddress": associate_public_ip,
        }
        primary_nic = dict((k, v) for k, v in primary_nic.items() if v)

        # If empty NIC spec but primary NIC values provided, create NIC from
        # them.
        if primary_nic and not nic_spec:
            nic_spec = [primary_nic]
            nic_spec[0]["DeviceIndex"] = 0

        # Flesh out data structures and associations
        for nic in nic_spec:
            device_index = int(nic.get("DeviceIndex"))

            nic_id = nic.get("NetworkInterfaceId")
            if nic_id:
                # If existing NIC found, use it.
                use_nic = self.ec2_backend.get_network_interface(nic_id)
                use_nic.device_index = device_index
                use_nic.public_ip_auto_assign = False

            else:
                # If primary NIC values provided, use them for the primary NIC.
                if device_index == 0 and primary_nic:
                    nic.update(primary_nic)

                if "SubnetId" in nic:
                    subnet = self.ec2_backend.get_subnet(nic["SubnetId"])
                else:
                    # Get default Subnet
                    zone = self._placement.zone
                    subnet = self.ec2_backend.get_default_subnet(availability_zone=zone)

                group_ids = nic.get("SecurityGroupId") or []
                if security_groups:
                    group_ids.extend([group.id for group in security_groups])

                use_nic = self.ec2_backend.create_network_interface(
                    subnet,
                    nic.get("PrivateIpAddress"),
                    device_index=device_index,
                    public_ip_auto_assign=nic.get("AssociatePublicIpAddress", False),
                    group_ids=group_ids,
                )

            self.attach_eni(use_nic, device_index)

    def attach_eni(self, eni, device_index):
        device_index = int(device_index)
        self.nics[device_index] = eni

        # This is used upon associate/disassociate public IP.
        eni.instance = self
        eni.attachment_id = random_eni_attach_id()
        eni.attach_time = utc_date_and_time()
        eni.status = "in-use"
        eni.device_index = device_index

        return eni.attachment_id

    def detach_eni(self, eni):
        self.nics.pop(eni.device_index, None)
        eni.instance = None
        eni.attachment_id = None
        eni.attach_time = None
        eni.status = "available"
        eni.device_index = None

    @classmethod
    def has_cfn_attr(cls, attr):
        return attr in [
            "AvailabilityZone",
            "PrivateDnsName",
            "PublicDnsName",
            "PrivateIp",
            "PublicIp",
        ]

    def get_cfn_attribute(self, attribute_name):
        from moto.cloudformation.exceptions import UnformattedGetAttTemplateException

        if attribute_name == "AvailabilityZone":
            return self.placement
        elif attribute_name == "PrivateDnsName":
            return self.private_dns
        elif attribute_name == "PublicDnsName":
            return self.public_dns
        elif attribute_name == "PrivateIp":
            return self.private_ip
        elif attribute_name == "PublicIp":
            return self.public_ip
        raise UnformattedGetAttTemplateException()

    def applies(self, filters):
        if filters:
            applicable = False
            for f in filters:
                acceptable_values = f["values"]
                if f["name"] == "instance-state-name":
                    if self._state.name in acceptable_values:
                        applicable = True
                if f["name"] == "instance-state-code":
                    if str(self._state.code) in acceptable_values:
                        applicable = True
            return applicable
        # If there are no filters, all instances are valid
        return True


class InstanceBackend:
    def __init__(self):
        self.reservations = OrderedDict()

    def get_instance(self, instance_id):
        for instance in self.all_instances():
            if instance.id == instance_id:
                return instance
        raise InvalidInstanceIdError(instance_id)

    def add_instances(self, image_id, count, user_data, security_group_names, **kwargs):
        location_type = "availability-zone" if kwargs.get("placement") else "region"
        default_region = "us-east-1"
        if settings.ENABLE_KEYPAIR_VALIDATION:
            self.describe_key_pairs(key_names=[kwargs.get("key_name")])
        if settings.ENABLE_AMI_VALIDATION:
            self.describe_images(ami_ids=[image_id] if image_id else [])
        valid_instance_types = INSTANCE_TYPE_OFFERINGS[location_type]
        if "region_name" in kwargs and kwargs.get("placement"):
            valid_availability_zones = {
                instance["Location"]
                for instance in valid_instance_types[kwargs["region_name"]]
            }
            if kwargs["placement"] not in valid_availability_zones:
                raise AvailabilityZoneNotFromRegionError(kwargs["placement"])
        match_filters = InstanceTypeOfferingBackend().matches_filters
        if not kwargs["is_instance_type_default"] and not any(
            {
                match_filters(
                    valid_instance,
                    {"instance-type": kwargs["instance_type"]},
                    location_type,
                )
                for valid_instance in valid_instance_types.get(
                    kwargs["region_name"]
                    if "region_name" in kwargs
                    else default_region,
                    {},
                )
            },
        ):
            if settings.EC2_ENABLE_INSTANCE_TYPE_VALIDATION:
                raise InvalidInstanceTypeError(kwargs["instance_type"])
        new_reservation = Reservation()
        new_reservation.id = random_reservation_id()

        security_groups = [
            self.get_security_group_by_name_or_id(name) for name in security_group_names
        ]

        for sg_id in kwargs.pop("security_group_ids", []):
            if isinstance(sg_id, str):
                security_groups.append(self.get_security_group_from_id(sg_id))
            else:
                security_groups.append(sg_id)

        self.reservations[new_reservation.id] = new_reservation

        tags = kwargs.pop("tags", {})
        instance_tags = tags.get("instance", {})
        volume_tags = tags.get("volume", {})

        for index in range(count):
            kwargs["ami_launch_index"] = index
            new_instance = Instance(
                self, image_id, user_data, security_groups, **kwargs
            )
            new_reservation.instances.append(new_instance)
            new_instance.add_tags(instance_tags)
            block_device_mappings = None
            if "block_device_mappings" not in kwargs:
                new_instance.setup_defaults()
            if "block_device_mappings" in kwargs:
                block_device_mappings = kwargs["block_device_mappings"]
            elif kwargs.get("launch_template"):
                template = self._get_template_from_args(kwargs["launch_template"])
                block_device_mappings = template.data.get("BlockDeviceMapping")
            elif kwargs.get("launch_config"):
                block_device_mappings = kwargs[
                    "launch_config"
                ].block_device_mapping_dict
            if block_device_mappings:
                for block_device in block_device_mappings:
                    device_name = block_device["DeviceName"]
                    volume_size = block_device["Ebs"].get("VolumeSize")
                    volume_type = block_device["Ebs"].get("VolumeType")
                    snapshot_id = block_device["Ebs"].get("SnapshotId")
                    encrypted = block_device["Ebs"].get("Encrypted", False)
                    if isinstance(encrypted, str):
                        encrypted = encrypted.lower() == "true"
                    delete_on_termination = block_device["Ebs"].get(
                        "DeleteOnTermination", False
                    )
                    kms_key_id = block_device["Ebs"].get("KmsKeyId")

                    if block_device.get("NoDevice") != "":
                        new_instance.add_block_device(
                            volume_size,
                            device_name,
                            snapshot_id,
                            encrypted,
                            delete_on_termination,
                            kms_key_id,
                            volume_type=volume_type,
                        )
            if kwargs.get("instance_market_options"):
                new_instance.lifecycle = "spot"
            # Tag all created volumes.
            for _, device in new_instance.get_block_device_mapping:
                volumes = self.describe_volumes(volume_ids=[device.volume_id])
                for volume in volumes:
                    volume.add_tags(volume_tags)

        return new_reservation

    def run_instances(self):
        """
        The Placement-parameter is validated to verify the availability-zone exists for the current region.

        The InstanceType-parameter can be validated, to see if it is a known instance-type.
        Enable this validation by setting the environment variable `MOTO_EC2_ENABLE_INSTANCE_TYPE_VALIDATION=true`

        The ImageId-parameter can be validated, to see if it is a known AMI.
        Enable this validation by setting the environment variable `MOTO_ENABLE_AMI_VALIDATION=true`

        The KeyPair-parameter can be validated, to see if it is a known key-pair.
        Enable this validation by setting the environment variable `MOTO_ENABLE_KEYPAIR_VALIDATION=true`
        """
        # Logic resides in add_instances
        # Fake method here to make implementation coverage script aware that this method is implemented
        pass

    def start_instances(self, instance_ids):
        started_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.start()
            started_instances.append(instance)

        return started_instances

    def stop_instances(self, instance_ids):
        stopped_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.stop()
            stopped_instances.append(instance)

        return stopped_instances

    def terminate_instances(self, instance_ids):
        terminated_instances = []
        if not instance_ids:
            raise EC2ClientError(
                "InvalidParameterCombination", "No instances specified"
            )
        for instance in self.get_multi_instances_by_id(instance_ids):
            if instance.disable_api_termination == "true":
                raise OperationNotPermitted4(instance.id)
            instance.terminate()
            terminated_instances.append(instance)

        return terminated_instances

    def reboot_instances(self, instance_ids):
        rebooted_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            instance.reboot()
            rebooted_instances.append(instance)

        return rebooted_instances

    def modify_instance_attribute(self, instance_id, key, value):
        instance = self.get_instance(instance_id)
        setattr(instance, key, value)
        return instance

    def modify_instance_security_groups(self, instance_id, new_group_id_list):
        instance = self.get_instance(instance_id)
        new_group_list = []
        for new_group_id in new_group_id_list:
            new_group_list.append(self.get_security_group_from_id(new_group_id))
        setattr(instance, "security_groups", new_group_list)
        return instance

    def describe_instance_attribute(self, instance_id, attribute):
        if attribute not in Instance.VALID_ATTRIBUTES:
            raise InvalidParameterValueErrorUnknownAttribute(attribute)

        if attribute == "groupSet":
            key = "security_groups"
        else:
            key = camelcase_to_underscores(attribute)
        instance = self.get_instance(instance_id)
        value = getattr(instance, key)
        return instance, value

    def describe_instance_credit_specifications(self, instance_ids):
        queried_instances = []
        for instance in self.get_multi_instances_by_id(instance_ids):
            queried_instances.append(instance)
        return queried_instances

    def all_instances(self, filters=None):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.applies(filters):
                    instances.append(instance)
        return instances

    def all_running_instances(self, filters=None):
        instances = []
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.state_code == 16 and instance.applies(filters):
                    instances.append(instance)
        return instances

    def get_multi_instances_by_id(self, instance_ids, filters=None):
        """
        :param instance_ids: A string list with instance ids
        :return: A list with instance objects
        """
        result = []

        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id in instance_ids:
                    if instance.applies(filters):
                        result.append(instance)

        if instance_ids and len(instance_ids) > len(result):
            result_ids = [i.id for i in result]
            missing_instance_ids = [i for i in instance_ids if i not in result_ids]
            raise InvalidInstanceIdError(missing_instance_ids)

        return result

    def get_instance_by_id(self, instance_id):
        for reservation in self.all_reservations():
            for instance in reservation.instances:
                if instance.id == instance_id:
                    return instance

    def get_reservations_by_instance_ids(self, instance_ids, filters=None):
        """Go through all of the reservations and filter to only return those
        associated with the given instance_ids.
        """
        reservations = []
        for reservation in self.all_reservations():
            reservation_instance_ids = [
                instance.id for instance in reservation.instances
            ]
            matching_reservation = any(
                instance_id in reservation_instance_ids for instance_id in instance_ids
            )
            if matching_reservation:
                reservation.instances = [
                    instance
                    for instance in reservation.instances
                    if instance.id in instance_ids
                ]
                reservations.append(reservation)
        found_instance_ids = [
            instance.id
            for reservation in reservations
            for instance in reservation.instances
        ]
        if len(found_instance_ids) != len(instance_ids):
            invalid_id = list(set(instance_ids).difference(set(found_instance_ids)))[0]
            raise InvalidInstanceIdError(invalid_id)
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations

    def describe_instances(self, filters=None):
        return self.all_reservations(filters)

    def describe_instance_status(self, instance_ids, include_all_instances, filters):
        if instance_ids:
            return self.get_multi_instances_by_id(instance_ids, filters)
        elif include_all_instances:
            return self.all_instances(filters)
        else:
            return self.all_running_instances(filters)

    def all_reservations(self, filters=None):
        reservations = [
            copy.copy(reservation) for reservation in self.reservations.copy().values()
        ]
        if filters is not None:
            reservations = filter_reservations(reservations, filters)
        return reservations

    def _get_template_from_args(self, launch_template_arg):
        template = (
            self.describe_launch_templates(
                template_ids=[launch_template_arg["LaunchTemplateId"]]
            )[0]
            if "LaunchTemplateId" in launch_template_arg
            else self.describe_launch_templates(
                template_names=[launch_template_arg["LaunchTemplateName"]]
            )[0]
        )
        version = launch_template_arg.get("Version", template.latest_version_number)
        template_version = template.get_version(int(version))
        return template_version
