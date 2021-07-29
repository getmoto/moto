"""Implement models for EFS resources.

See AWS docs for details:
https://docs.aws.amazon.com/efs/latest/ug/whatisefs.html
"""

from __future__ import unicode_literals

import json
import time
from copy import deepcopy
from hashlib import md5

from boto3 import Session

from moto.core import ACCOUNT_ID, BaseBackend, CloudFormationModel
from moto.core.utils import (
    camelcase_to_underscores,
    get_random_hex,
    underscores_to_camelcase,
)
from moto.ec2 import ec2_backends
from moto.ec2.exceptions import InvalidSubnetIdError
from moto.efs.exceptions import (
    BadRequest,
    FileSystemAlreadyExists,
    FileSystemInUse,
    FileSystemNotFound,
    MountTargetConflict,
    MountTargetNotFound,
    PolicyNotFound,
    SubnetNotFound,
    SecurityGroupNotFound,
    SecurityGroupLimitExceeded,
)


def _lookup_az_id(az_name):
    """Find the Availability zone ID given the AZ name."""
    ec2 = ec2_backends[az_name[:-1]]
    for zone in ec2.describe_availability_zones():
        if zone.name == az_name:
            return zone.zone_id


class FileSystem(CloudFormationModel):
    """A model for an EFS File System Volume."""

    def __init__(
        self,
        region_name,
        creation_token,
        file_system_id,
        performance_mode="generalPurpose",
        encrypted=False,
        kms_key_id=None,
        throughput_mode="bursting",
        provisioned_throughput_in_mibps=None,
        availability_zone_name=None,
        backup=False,
        lifecycle_policies=None,
        file_system_policy=None,
        tags=None,
    ):
        if availability_zone_name:
            backup = True
        if kms_key_id and not encrypted:
            raise BadRequest('If kms_key_id given, "encrypted" must be True.')

        # Save given parameters
        self.creation_token = creation_token
        self.performance_mode = performance_mode
        self.encrypted = encrypted
        self.kms_key_id = kms_key_id
        self.throughput_mode = throughput_mode
        self.provisioned_throughput_in_mibps = provisioned_throughput_in_mibps
        self.availability_zone_name = availability_zone_name
        self.availability_zone_id = None
        if self.availability_zone_name:
            self.availability_zone_id = _lookup_az_id(self.availability_zone_name)
        self._backup = backup
        self.lifecycle_policies = lifecycle_policies
        self.file_system_policy = file_system_policy

        # Validate tag structure.
        if tags is None:
            self.tags = []
        else:
            if (
                not isinstance(tags, list)
                or not all(isinstance(tag, dict) for tag in tags)
                or not all(set(tag.keys()) == {"Key", "Value"} for tag in tags)
            ):
                raise ValueError("Invalid tags: {}".format(tags))
            else:
                self.tags = tags

        # Generate AWS-assigned parameters
        self.file_system_id = file_system_id
        self.file_system_arn = "arn:aws:elasticfilesystem:{region}:{user_id}:file-system/{file_system_id}".format(
            region=region_name, user_id=ACCOUNT_ID, file_system_id=self.file_system_id
        )
        self.creation_time = time.time()
        self.owner_id = ACCOUNT_ID

        # Initialize some state parameters
        self.life_cycle_state = "available"
        self._mount_targets = {}
        self._size_value = 0

    @property
    def size_in_bytes(self):
        return {
            "Value": self._size_value,
            "ValueInIA": 0,
            "ValueInStandard": self._size_value,
            "Timestamp": time.time(),
        }

    @property
    def physical_resource_id(self):
        return self.file_system_id

    @property
    def number_of_mount_targets(self):
        return len(self._mount_targets)

    @property
    def backup_policy(self):
        if self._backup:
            return {"Status": "ENABLED"}
        else:
            return

    def info_json(self):
        ret = {
            underscores_to_camelcase(k.capitalize()): v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }
        ret["SizeInBytes"] = self.size_in_bytes
        ret["NumberOfMountTargets"] = self.number_of_mount_targets
        return ret

    def add_mount_target(self, subnet, mount_target):
        # Check that the mount target doesn't violate constraints.
        for other_mount_target in self._mount_targets.values():
            if other_mount_target.subnet_vpc_id != subnet.vpc_id:
                raise MountTargetConflict(
                    "requested subnet for new mount target is not in the same VPC as existing mount targets"
                )

        if subnet.availability_zone in self._mount_targets:
            raise MountTargetConflict("mount target already exists in this AZ")

        self._mount_targets[subnet.availability_zone] = mount_target

    def has_mount_target(self, subnet):
        return subnet.availability_zone in self._mount_targets

    def iter_mount_targets(self):
        for mt in self._mount_targets.values():
            yield mt

    def remove_mount_target(self, subnet):
        del self._mount_targets[subnet.availability_zone]

    @staticmethod
    def cloudformation_name_type():
        return

    @staticmethod
    def cloudformation_type():
        return "AWS::EFS::FileSystem"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-efs-filesystem.html
        props = deepcopy(cloudformation_json["Properties"])
        props = {camelcase_to_underscores(k): v for k, v in props.items()}
        if "file_system_tags" in props:
            props["tags"] = props.pop("file_system_tags")
        if "backup_policy" in props:
            if "status" not in props["backup_policy"]:
                raise ValueError("BackupPolicy must be of type BackupPolicy.")
            status = props.pop("backup_policy")["status"]
            if status not in ["ENABLED", "DISABLED"]:
                raise ValueError('Invalid status: "{}".'.format(status))
            props["backup"] = status == "ENABLED"
        if "bypass_policy_lockout_safety_check" in props:
            raise ValueError(
                "BypassPolicyLockoutSafetyCheck not currently "
                "supported by AWS Cloudformation."
            )

        return efs_backends[region_name].create_file_system(resource_name, **props)

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        raise NotImplementedError(
            "Update of EFS File System via cloudformation is not yet implemented."
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        return efs_backends[region_name].delete_file_system(resource_name)


class MountTarget(CloudFormationModel):
    """A model for an EFS Mount Target."""

    def __init__(self, file_system, subnet, ip_address, security_groups):
        # Set the simple given parameters.
        self.file_system_id = file_system.file_system_id
        self._file_system = file_system
        self._file_system.add_mount_target(subnet, self)
        self.subnet_id = subnet.id
        self._subnet = subnet
        self.vpc_id = subnet.vpc_id
        self.security_groups = security_groups

        # Check the number of security groups.
        if self.security_groups is not None and len(self.security_groups) > 5:
            raise SecurityGroupLimitExceeded(
                "The maximum number of security groups per interface has been reached."
            )

        # Get an IP address if needed, otherwise validate the one we're given.
        if ip_address is None:
            ip_address = subnet.get_available_subnet_ip(self)
        else:
            try:
                subnet.request_ip(ip_address, self)
            except Exception as e:
                if "IP" in str(e) and "CIDR" in str(e):
                    raise BadRequest(
                        "Address does not fall within the subnet's address range"
                    )
                else:
                    raise e
        self.ip_address = ip_address

        # Init non-user-assigned values.
        self.owner_id = ACCOUNT_ID
        self.mount_target_id = "fsmt-{}".format(get_random_hex())
        self.life_cycle_state = "available"
        self.network_interface_id = None
        self.availability_zone_id = subnet.availability_zone_id
        self.availability_zone_name = subnet.availability_zone

    def clean_up(self):
        self._file_system.remove_mount_target(self._subnet)
        self._subnet.del_subnet_ip(self.ip_address)

    def set_network_interface(self, network_interface):
        self.network_interface_id = network_interface.id

    def info_json(self):
        ret = {
            underscores_to_camelcase(k.capitalize()): v
            for k, v in self.__dict__.items()
            if not k.startswith("_")
        }
        return ret

    @property
    def physical_resource_id(self):
        return self.mounted_target_id

    @property
    def subnet_vpc_id(self):
        return self._subnet.vpc_id

    @staticmethod
    def cloudformation_name_type():
        pass

    @staticmethod
    def cloudformation_type():
        return "AWS::EFS::MountTarget"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-efs-mounttarget.html
        props = deepcopy(cloudformation_json["Properties"])
        props = {camelcase_to_underscores(k): v for k, v in props.items()}
        return efs_backends[region_name].create_mount_target(**props)

    @classmethod
    def update_from_cloudformation_json(
        cls, original_resource, new_resource_name, cloudformation_json, region_name
    ):
        raise NotImplementedError(
            "Updates of EFS Mount Target via cloudformation are not yet implemented."
        )

    @classmethod
    def delete_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name
    ):
        return efs_backends[region_name].delete_mount_target(resource_name)


class EFSBackend(BaseBackend):
    """The backend manager of EFS resources.

    This is the state-machine for each region, tracking the file systems, mount targets,
    and eventually access points that are deployed. Creating, updating, and destroying
    such resources should always go through this class.
    """

    def __init__(self, region_name=None):
        super(EFSBackend, self).__init__()
        self.region_name = region_name
        self.creation_tokens = set()
        self.file_systems_by_id = {}
        self.mount_targets_by_id = {}
        self.next_markers = {}

    def reset(self):
        # preserve region
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    def _mark_description(self, corpus, max_items):
        if max_items < len(corpus):
            new_corpus = corpus[max_items:]
            new_hash = md5(json.dumps(new_corpus).encode("utf-8"))
            next_marker = new_hash.hexdigest()
            self.next_markers[next_marker] = new_corpus
        else:
            next_marker = None
        return next_marker

    @property
    def ec2_backend(self):
        return ec2_backends[self.region_name]

    def create_file_system(self, creation_token, **params):
        """Create a new EFS File System Volume.

        https://docs.aws.amazon.com/efs/latest/ug/API_CreateFileSystem.html
        """
        if not creation_token:
            raise ValueError("No creation token given.")
        if creation_token in self.creation_tokens:
            raise FileSystemAlreadyExists(creation_token)

        # Create a new file system ID:
        def make_id():
            return "fs-{}".format(get_random_hex())

        fsid = make_id()
        while fsid in self.file_systems_by_id:
            fsid = make_id()
        self.file_systems_by_id[fsid] = FileSystem(
            self.region_name,
            creation_token,
            fsid,
            **{k: v for k, v in params.items() if v is not None}
        )
        self.creation_tokens.add(creation_token)
        return self.file_systems_by_id[fsid]

    def describe_file_systems(self, marker, max_items, creation_token, file_system_id):
        """Describe all the EFS File Systems, or specific File Systems.

        https://docs.aws.amazon.com/efs/latest/ug/API_DescribeFileSystems.html
        """
        # Restrict the possible corpus of resules based on inputs.
        if creation_token and file_system_id:
            raise BadRequest(
                "Request cannot contain both a file system ID and a creation token."
            )
        elif creation_token:
            # Handle the creation token case.
            corpus = []
            for fs in self.file_systems_by_id.values():
                if fs.creation_token == creation_token:
                    corpus.append(fs.info_json())
        elif file_system_id:
            # Handle the case that a file_system_id is given.
            if file_system_id not in self.file_systems_by_id:
                raise FileSystemNotFound(file_system_id)
            corpus = [self.file_systems_by_id[file_system_id]]
        elif marker is not None:
            # Handle the case that a marker is given.
            if marker not in self.next_markers:
                raise BadRequest("Invalid Marker")
            corpus = self.next_markers[marker]
        else:
            # Handle the vanilla case.
            corpus = [fs.info_json() for fs in self.file_systems_by_id.values()]

        # Handle the max_items parameter.
        file_systems = corpus[:max_items]
        next_marker = self._mark_description(corpus, max_items)
        return next_marker, file_systems

    def create_mount_target(
        self, file_system_id, subnet_id, ip_address=None, security_groups=None
    ):
        """Create a new EFS Mount Target for a given File System to a given subnet.

        Note that you can only create one mount target for each availability zone
        (which is implied by the subnet ID).

        https://docs.aws.amazon.com/efs/latest/ug/API_CreateMountTarget.html
        """
        # Get the relevant existing resources
        try:
            subnet = self.ec2_backend.get_subnet(subnet_id)
        except InvalidSubnetIdError:
            raise SubnetNotFound(subnet_id)
        if file_system_id not in self.file_systems_by_id:
            raise FileSystemNotFound(file_system_id)
        file_system = self.file_systems_by_id[file_system_id]

        # Validate the security groups.
        if security_groups:
            sg_lookup = {sg.id for sg in self.ec2_backend.describe_security_groups()}
            for sg_id in security_groups:
                if sg_id not in sg_lookup:
                    raise SecurityGroupNotFound(sg_id)

        # Create the new mount target
        mount_target = MountTarget(file_system, subnet, ip_address, security_groups)

        # Establish the network interface.
        network_interface = self.ec2_backend.create_network_interface(
            subnet, [mount_target.ip_address], group_ids=security_groups
        )
        mount_target.set_network_interface(network_interface)

        # Record the new mount target
        self.mount_targets_by_id[mount_target.mount_target_id] = mount_target
        return mount_target

    def describe_mount_targets(
        self, max_items, file_system_id, mount_target_id, access_point_id, marker
    ):
        """Describe the mount targets given a mount target ID or a file system ID.

        Note that as of this writing access points, and thus access point IDs are not
        supported.

        https://docs.aws.amazon.com/efs/latest/ug/API_DescribeMountTargets.html
        """
        # Restrict the possible corpus of results based on inputs.
        if not (bool(file_system_id) ^ bool(mount_target_id) ^ bool(access_point_id)):
            raise BadRequest("Must specify exactly one mutually exclusive parameter.")
        elif file_system_id:
            # Handle the case that a file_system_id is given.
            if file_system_id not in self.file_systems_by_id:
                raise FileSystemNotFound(file_system_id)
            corpus = [
                mt.info_json()
                for mt in self.file_systems_by_id[file_system_id].iter_mount_targets()
            ]
        elif mount_target_id:
            if mount_target_id not in self.mount_targets_by_id:
                raise MountTargetNotFound(mount_target_id)
            # Handle mount target specification case.
            corpus = [self.mount_targets_by_id[mount_target_id].info_json()]
        else:
            # We don't handle access_point_id's yet.
            assert False, "Moto does not yet support EFS access points."

        # Handle the case that a marker is given. Note that the handling is quite
        # different from that in describe_file_systems.
        if marker is not None:
            if marker not in self.next_markers:
                raise BadRequest("Invalid Marker")
            corpus_mtids = {m["MountTargetId"] for m in corpus}
            marked_mtids = {m["MountTargetId"] for m in self.next_markers[marker]}
            mt_ids = corpus_mtids & marked_mtids
            corpus = [self.mount_targets_by_id[mt_id].info_json() for mt_id in mt_ids]

        # Handle the max_items parameter.
        mount_targets = corpus[:max_items]
        next_marker = self._mark_description(corpus, max_items)
        return next_marker, mount_targets

    def delete_file_system(self, file_system_id):
        """Delete the file system specified by the given file_system_id.

        Note that mount targets must be deleted first.

        https://docs.aws.amazon.com/efs/latest/ug/API_DeleteFileSystem.html
        """
        if file_system_id not in self.file_systems_by_id:
            raise FileSystemNotFound(file_system_id)

        file_system = self.file_systems_by_id[file_system_id]
        if file_system.number_of_mount_targets > 0:
            raise FileSystemInUse(
                "Must delete all mount targets before deleting file system."
            )

        del self.file_systems_by_id[file_system_id]
        self.creation_tokens.remove(file_system.creation_token)
        return

    def delete_mount_target(self, mount_target_id):
        """Delete a mount target specified by the given mount_target_id.

        Note that this will also delete a network interface.

        https://docs.aws.amazon.com/efs/latest/ug/API_DeleteMountTarget.html
        """
        if mount_target_id not in self.mount_targets_by_id:
            raise MountTargetNotFound(mount_target_id)

        mount_target = self.mount_targets_by_id[mount_target_id]
        self.ec2_backend.delete_network_interface(mount_target.network_interface_id)
        del self.mount_targets_by_id[mount_target_id]
        mount_target.clean_up()
        return

    def describe_backup_policy(self, file_system_id):
        backup_policy = self.file_systems_by_id[file_system_id].backup_policy
        if not backup_policy:
            raise PolicyNotFound("None")
        return backup_policy


efs_backends = {}
for region in Session().get_available_regions("efs"):
    efs_backends[region] = EFSBackend(region)
for region in Session().get_available_regions("efs", partition_name="aws-us-gov"):
    efs_backends[region] = EFSBackend(region)
for region in Session().get_available_regions("efs", partition_name="aws-cn"):
    efs_backends[region] = EFSBackend(region)
