import json
import re
from os import environ
from moto.utilities.utils import load_resource
from ..exceptions import (
    InvalidAMIIdError,
    InvalidAMIAttributeItemValueError,
    MalformedAMIIdError,
    InvalidTaggableResourceType,
    UnvailableAMIIdError,
)
from .core import TaggedEC2Resource
from ..utils import (
    random_ami_id,
    generic_filter,
    utc_date_and_time,
)


if "MOTO_AMIS_PATH" in environ:
    with open(environ.get("MOTO_AMIS_PATH"), "r", encoding="utf-8") as f:
        AMIS = json.load(f)
else:
    AMIS = load_resource(__name__, "../resources/amis.json")


class Ami(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        ami_id,
        instance=None,
        source_ami=None,
        name=None,
        description=None,
        owner_id=None,
        owner_alias=None,
        public=False,
        virtualization_type=None,
        architecture=None,
        state="available",
        creation_date=None,
        platform=None,
        image_type="machine",
        image_location=None,
        hypervisor=None,
        root_device_type="standard",
        root_device_name="/dev/sda1",
        sriov="simple",
        region_name="us-east-1a",
        snapshot_description=None,
    ):
        self.ec2_backend = ec2_backend
        self.id = ami_id
        self.state = state
        self.name = name
        self.image_type = image_type
        self.image_location = image_location
        self.owner_id = owner_id or ec2_backend.account_id
        self.owner_alias = owner_alias
        self.description = description
        self.virtualization_type = virtualization_type
        self.architecture = architecture
        self.kernel_id = None
        self.platform = platform
        self.hypervisor = hypervisor
        self.root_device_name = root_device_name
        self.root_device_type = root_device_type
        self.sriov = sriov
        self.creation_date = creation_date or utc_date_and_time()

        if instance:
            self.instance = instance
            self.instance_id = instance.id
            self.virtualization_type = instance.virtualization_type
            self.architecture = instance.architecture
            self.kernel_id = instance.kernel
            self.platform = instance.platform

        elif source_ami:
            """
            http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/CopyingAMIs.html
            "We don't copy launch permissions, user-defined tags, or Amazon S3 bucket permissions from the source AMI to the new AMI."
            ~ 2014.09.29
            """
            self.virtualization_type = source_ami.virtualization_type
            self.architecture = source_ami.architecture
            self.kernel_id = source_ami.kernel_id
            self.platform = source_ami.platform
            if not name:
                self.name = source_ami.name
            if not description:
                self.description = source_ami.description

        self.launch_permission_groups = set()
        self.launch_permission_users = set()

        if public:
            self.launch_permission_groups.add("all")

        # AWS auto-creates these, we should reflect the same.
        volume = self.ec2_backend.create_volume(size=15, zone_name=region_name)
        snapshot_description = (
            snapshot_description or f"Auto-created snapshot for AMI {self.id}"
        )
        self.ebs_snapshot = self.ec2_backend.create_snapshot(
            volume.id, snapshot_description, self.owner_id, from_ami=ami_id
        )
        self.ec2_backend.delete_volume(volume.id)

    @property
    def is_public(self):
        return "all" in self.launch_permission_groups

    @property
    def is_public_string(self):
        return str(self.is_public).lower()

    def get_filter_value(self, filter_name):
        if filter_name == "virtualization-type":
            return self.virtualization_type
        elif filter_name == "kernel-id":
            return self.kernel_id
        elif filter_name in ["architecture", "platform"]:
            return getattr(self, filter_name)
        elif filter_name == "image-id":
            return self.id
        elif filter_name == "is-public":
            return self.is_public_string
        elif filter_name == "state":
            return self.state
        elif filter_name == "name":
            return self.name
        elif filter_name == "owner-id":
            return self.owner_id
        elif filter_name == "owner-alias":
            return self.owner_alias
        else:
            return super().get_filter_value(filter_name, "DescribeImages")


class AmiBackend:
    AMI_REGEX = re.compile("ami-[a-z0-9]+")

    def __init__(self):
        self.amis = {}
        self.deleted_amis = list()
        self._load_amis()

    def _load_amis(self):
        for ami in AMIS:
            ami_id = ami["ami_id"]
            # we are assuming the default loaded amis are owned by amazon
            # owner_alias is required for terraform owner filters
            ami["owner_alias"] = "amazon"
            self.amis[ami_id] = Ami(self, **ami)
        if "MOTO_AMIS_PATH" not in environ:
            try:
                latest_amis = load_resource(
                    __name__, f"../resources/latest_amis/{self.region_name}.json"
                )
                for ami in latest_amis:
                    ami_id = ami["ami_id"]
                    ami["owner_alias"] = "amazon"
                    self.amis[ami_id] = Ami(self, **ami)
            except FileNotFoundError:
                # Will error on unknown (new) regions - just return an empty list here
                pass

    def create_image(
        self,
        instance_id,
        name=None,
        description=None,
        tag_specifications=None,
    ):
        # TODO: check that instance exists and pull info from it.
        ami_id = random_ami_id()
        instance = self.get_instance(instance_id)
        tags = []
        for tag_specification in tag_specifications:
            resource_type = tag_specification["ResourceType"]
            if resource_type == "image":
                tags += tag_specification["Tag"]
            elif resource_type == "snapshot":
                raise NotImplementedError()
            else:
                raise InvalidTaggableResourceType(resource_type)

        ami = Ami(
            self,
            ami_id,
            instance=instance,
            source_ami=None,
            name=name,
            description=description,
            owner_id=None,
            snapshot_description=f"Created by CreateImage({instance_id}) for {ami_id}",
        )
        for tag in tags:
            ami.add_tag(tag["Key"], tag["Value"])
        self.amis[ami_id] = ami
        return ami

    def copy_image(self, source_image_id, source_region, name=None, description=None):
        from ..models import ec2_backends

        source_ami = ec2_backends[self.account_id][source_region].describe_images(
            ami_ids=[source_image_id]
        )[0]
        ami_id = random_ami_id()
        ami = Ami(
            self,
            ami_id,
            instance=None,
            source_ami=source_ami,
            name=name,
            description=description,
        )
        self.amis[ami_id] = ami
        return ami

    def describe_images(self, ami_ids=(), filters=None, exec_users=None, owners=None):
        images = self.amis.copy().values()

        if len(ami_ids):
            # boto3 seems to default to just searching based on ami ids if that parameter is passed
            # and if no images are found, it raises an errors
            # Note that we can search for images that have been previously deleted, without raising any errors
            malformed_ami_ids = [
                ami_id for ami_id in ami_ids if not ami_id.startswith("ami-")
            ]
            if malformed_ami_ids:
                raise MalformedAMIIdError(malformed_ami_ids)

            images = [ami for ami in images if ami.id in ami_ids]
            deleted_images = [
                ami_id for ami_id in ami_ids if ami_id in self.deleted_amis
            ]
            if len(images) + len(deleted_images) == 0:
                raise InvalidAMIIdError(ami_ids)
        else:
            # Limit images by launch permissions
            if exec_users:
                tmp_images = []
                for ami in images:
                    for user_id in exec_users:
                        if user_id in ami.launch_permission_users:
                            tmp_images.append(ami)
                images = tmp_images

            # Limit by owner ids
            if owners:
                # support filtering by Owners=['self']
                if "self" in owners:
                    owners = list(
                        map(lambda o: self.account_id if o == "self" else o, owners)
                    )
                images = [
                    ami
                    for ami in images
                    if ami.owner_id in owners or ami.owner_alias in owners
                ]

            # Generic filters
            if filters:
                return generic_filter(filters, images)

        return images

    def deregister_image(self, ami_id):
        if ami_id in self.amis:
            self.amis.pop(ami_id)
            self.deleted_amis.append(ami_id)
            return True
        elif ami_id in self.deleted_amis:
            raise UnvailableAMIIdError(ami_id)
        raise InvalidAMIIdError(ami_id)

    def get_launch_permission_groups(self, ami_id):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        return ami.launch_permission_groups

    def get_launch_permission_users(self, ami_id):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        return ami.launch_permission_users

    def validate_permission_targets(self, user_ids=None, group=None):
        # If anything is invalid, nothing is added. (No partial success.)
        if user_ids:
            """
            AWS docs:
              "The AWS account ID is a 12-digit number, such as 123456789012, that you use to construct Amazon Resource Names (ARNs)."
              http://docs.aws.amazon.com/general/latest/gr/acct-identifiers.html
            """
            for user_id in user_ids:
                if len(user_id) != 12 or not user_id.isdigit():
                    raise InvalidAMIAttributeItemValueError("userId", user_id)

        if group and group != "all":
            raise InvalidAMIAttributeItemValueError("UserGroup", group)

    def add_launch_permission(self, ami_id, user_ids=None, group=None):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        self.validate_permission_targets(user_ids=user_ids, group=group)

        if user_ids:
            for user_id in user_ids:
                ami.launch_permission_users.add(user_id)

        if group:
            ami.launch_permission_groups.add(group)

        return True

    def register_image(self, name=None, description=None):
        ami_id = random_ami_id()
        ami = Ami(
            self,
            ami_id,
            instance=None,
            source_ami=None,
            name=name,
            description=description,
        )
        self.amis[ami_id] = ami
        return ami

    def remove_launch_permission(self, ami_id, user_ids=None, group=None):
        ami = self.describe_images(ami_ids=[ami_id])[0]
        self.validate_permission_targets(user_ids=user_ids, group=group)

        if user_ids:
            for user_id in user_ids:
                ami.launch_permission_users.discard(user_id)

        if group:
            ami.launch_permission_groups.discard(group)

        return True
