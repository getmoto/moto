from moto.core import ACCOUNT_ID
from moto.core.models import CloudFormationModel
from moto.kms import kms_backends
from moto.packages.boto.ec2.blockdevicemapping import BlockDeviceType
from ..exceptions import (
    InvalidAMIAttributeItemValueError,
    InvalidSnapshotIdError,
    InvalidSnapshotInUse,
    InvalidVolumeIdError,
    VolumeInUseError,
    InvalidVolumeAttachmentError,
    InvalidVolumeDetachmentError,
    InvalidParameterDependency,
)
from .core import TaggedEC2Resource
from ..utils import (
    random_snapshot_id,
    random_volume_id,
    generic_filter,
    utc_date_and_time,
)


class VolumeAttachment(CloudFormationModel):
    def __init__(self, volume, instance, device, status):
        self.volume = volume
        self.attach_time = utc_date_and_time()
        self.instance = instance
        self.device = device
        self.status = status

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-volumeattachment.html
        return "AWS::EC2::VolumeAttachment"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        instance_id = properties["InstanceId"]
        volume_id = properties["VolumeId"]

        ec2_backend = ec2_backends[region_name]
        attachment = ec2_backend.attach_volume(
            volume_id=volume_id,
            instance_id=instance_id,
            device_path=properties["Device"],
        )
        return attachment


class Volume(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        volume_id,
        size,
        zone,
        snapshot_id=None,
        encrypted=False,
        kms_key_id=None,
        volume_type=None,
    ):
        self.id = volume_id
        self.volume_type = volume_type or "gp2"
        self.size = size
        self.zone = zone
        self.create_time = utc_date_and_time()
        self.attachment = None
        self.snapshot_id = snapshot_id
        self.ec2_backend = ec2_backend
        self.encrypted = encrypted
        self.kms_key_id = kms_key_id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-volume.html
        return "AWS::EC2::Volume"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]

        ec2_backend = ec2_backends[region_name]
        volume = ec2_backend.create_volume(
            size=properties.get("Size"), zone_name=properties.get("AvailabilityZone")
        )
        return volume

    @property
    def physical_resource_id(self):
        return self.id

    @property
    def status(self):
        if self.attachment:
            return "in-use"
        else:
            return "available"

    def get_filter_value(self, filter_name):
        if filter_name.startswith("attachment") and not self.attachment:
            return None
        elif filter_name == "attachment.attach-time":
            return self.attachment.attach_time
        elif filter_name == "attachment.device":
            return self.attachment.device
        elif filter_name == "attachment.instance-id":
            return self.attachment.instance.id
        elif filter_name == "attachment.status":
            return self.attachment.status
        elif filter_name == "create-time":
            return self.create_time
        elif filter_name == "size":
            return self.size
        elif filter_name == "snapshot-id":
            return self.snapshot_id
        elif filter_name == "status":
            return self.status
        elif filter_name == "volume-id":
            return self.id
        elif filter_name == "encrypted":
            return str(self.encrypted).lower()
        elif filter_name == "availability-zone":
            return self.zone.name if self.zone else None
        else:
            return super().get_filter_value(filter_name, "DescribeVolumes")


class Snapshot(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        snapshot_id,
        volume,
        description,
        encrypted=False,
        owner_id=ACCOUNT_ID,
        from_ami=None,
    ):
        self.id = snapshot_id
        self.volume = volume
        self.description = description
        self.start_time = utc_date_and_time()
        self.create_volume_permission_groups = set()
        self.create_volume_permission_userids = set()
        self.ec2_backend = ec2_backend
        self.status = "completed"
        self.encrypted = encrypted
        self.owner_id = owner_id
        self.from_ami = from_ami

    def get_filter_value(self, filter_name):
        if filter_name == "description":
            return self.description
        elif filter_name == "snapshot-id":
            return self.id
        elif filter_name == "start-time":
            return self.start_time
        elif filter_name == "volume-id":
            return self.volume.id
        elif filter_name == "volume-size":
            return self.volume.size
        elif filter_name == "encrypted":
            return str(self.encrypted).lower()
        elif filter_name == "status":
            return self.status
        elif filter_name == "owner-id":
            return self.owner_id
        else:
            return super().get_filter_value(filter_name, "DescribeSnapshots")


class EBSBackend(object):
    def __init__(self):
        self.volumes = {}
        self.attachments = {}
        self.snapshots = {}
        super().__init__()

    def create_volume(
        self,
        size,
        zone_name,
        snapshot_id=None,
        encrypted=False,
        kms_key_id=None,
        volume_type=None,
    ):
        if kms_key_id and not encrypted:
            raise InvalidParameterDependency("KmsKeyId", "Encrypted")
        if encrypted and not kms_key_id:
            kms_key_id = self._get_default_encryption_key()
        volume_id = random_volume_id()
        zone = self.get_zone_by_name(zone_name)
        if snapshot_id:
            snapshot = self.get_snapshot(snapshot_id)
            if size is None:
                size = snapshot.volume.size
            if snapshot.encrypted:
                encrypted = snapshot.encrypted
        volume = Volume(
            self,
            volume_id=volume_id,
            size=size,
            zone=zone,
            snapshot_id=snapshot_id,
            encrypted=encrypted,
            kms_key_id=kms_key_id,
            volume_type=volume_type,
        )
        self.volumes[volume_id] = volume
        return volume

    def describe_volumes(self, volume_ids=None, filters=None):
        matches = self.volumes.copy().values()
        if volume_ids:
            matches = [vol for vol in matches if vol.id in volume_ids]
            if len(volume_ids) > len(matches):
                unknown_ids = set(volume_ids) - set(matches)
                raise InvalidVolumeIdError(unknown_ids)
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def get_volume(self, volume_id):
        volume = self.volumes.get(volume_id, None)
        if not volume:
            raise InvalidVolumeIdError(volume_id)
        return volume

    def delete_volume(self, volume_id):
        if volume_id in self.volumes:
            volume = self.volumes[volume_id]
            if volume.attachment:
                raise VolumeInUseError(volume_id, volume.attachment.instance.id)
            return self.volumes.pop(volume_id)
        raise InvalidVolumeIdError(volume_id)

    def attach_volume(
        self, volume_id, instance_id, device_path, delete_on_termination=False
    ):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        if not volume or not instance:
            return False

        volume.attachment = VolumeAttachment(volume, instance, device_path, "attached")
        # Modify instance to capture mount of block device.
        bdt = BlockDeviceType(
            volume_id=volume_id,
            status=volume.status,
            size=volume.size,
            attach_time=utc_date_and_time(),
            delete_on_termination=delete_on_termination,
        )
        instance.block_device_mapping[device_path] = bdt
        return volume.attachment

    def detach_volume(self, volume_id, instance_id, device_path):
        volume = self.get_volume(volume_id)
        instance = self.get_instance(instance_id)

        old_attachment = volume.attachment
        if not old_attachment:
            raise InvalidVolumeAttachmentError(volume_id, instance_id)
        device_path = device_path or old_attachment.device

        try:
            del instance.block_device_mapping[device_path]
        except KeyError:
            raise InvalidVolumeDetachmentError(volume_id, instance_id, device_path)

        old_attachment.status = "detached"

        volume.attachment = None
        return old_attachment

    def create_snapshot(self, volume_id, description, owner_id=None, from_ami=None):
        snapshot_id = random_snapshot_id()
        volume = self.get_volume(volume_id)
        params = [self, snapshot_id, volume, description, volume.encrypted]
        if owner_id:
            params.append(owner_id)
        if from_ami:
            params.append(from_ami)
        snapshot = Snapshot(*params)
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def create_snapshots(self, instance_spec, description, tags):
        """
        The CopyTagsFromSource-parameter is not yet implemented.
        """
        instance = self.get_instance(instance_spec["InstanceId"])
        block_device_mappings = instance.block_device_mapping

        if str(instance_spec.get("ExcludeBootVolume", False)).lower() == "true":
            volumes = [
                m.volume_id
                for k, m in block_device_mappings.items()
                if k != instance.root_device_name
            ]
        else:
            volumes = [m.volume_id for m in block_device_mappings.values()]

        snapshots = [
            self.create_snapshot(v_id, description=description) for v_id in volumes
        ]
        for snapshot in snapshots:
            snapshot.add_tags(tags)
        return snapshots

    def describe_snapshots(self, snapshot_ids=None, filters=None):
        matches = self.snapshots.copy().values()
        if snapshot_ids:
            matches = [snap for snap in matches if snap.id in snapshot_ids]
            if len(snapshot_ids) > len(matches):
                raise InvalidSnapshotIdError()
        if filters:
            matches = generic_filter(filters, matches)
        return matches

    def copy_snapshot(self, source_snapshot_id, source_region, description=None):
        from ..models import ec2_backends

        source_snapshot = ec2_backends[source_region].describe_snapshots(
            snapshot_ids=[source_snapshot_id]
        )[0]
        snapshot_id = random_snapshot_id()
        snapshot = Snapshot(
            self,
            snapshot_id,
            volume=source_snapshot.volume,
            description=description,
            encrypted=source_snapshot.encrypted,
        )
        self.snapshots[snapshot_id] = snapshot
        return snapshot

    def get_snapshot(self, snapshot_id):
        snapshot = self.snapshots.get(snapshot_id, None)
        if not snapshot:
            raise InvalidSnapshotIdError()
        return snapshot

    def delete_snapshot(self, snapshot_id):
        if snapshot_id in self.snapshots:
            snapshot = self.snapshots[snapshot_id]
            if snapshot.from_ami and snapshot.from_ami in self.amis:
                raise InvalidSnapshotInUse(snapshot_id, snapshot.from_ami)
            return self.snapshots.pop(snapshot_id)
        raise InvalidSnapshotIdError()

    def get_create_volume_permission_groups(self, snapshot_id):
        snapshot = self.get_snapshot(snapshot_id)
        return snapshot.create_volume_permission_groups

    def get_create_volume_permission_userids(self, snapshot_id):
        snapshot = self.get_snapshot(snapshot_id)
        return snapshot.create_volume_permission_userids

    def add_create_volume_permission(self, snapshot_id, user_ids=None, groups=None):
        snapshot = self.get_snapshot(snapshot_id)
        if user_ids:
            snapshot.create_volume_permission_userids.update(user_ids)

        if groups and groups != ["all"]:
            raise InvalidAMIAttributeItemValueError("UserGroup", groups)
        else:
            snapshot.create_volume_permission_groups.update(groups)

        return True

    def remove_create_volume_permission(self, snapshot_id, user_ids=None, groups=None):
        snapshot = self.get_snapshot(snapshot_id)
        if user_ids:
            snapshot.create_volume_permission_userids.difference_update(user_ids)

        if groups and groups != ["all"]:
            raise InvalidAMIAttributeItemValueError("UserGroup", groups)
        else:
            snapshot.create_volume_permission_groups.difference_update(groups)

        return True

    def _get_default_encryption_key(self):
        # https://aws.amazon.com/kms/features/#AWS_Service_Integration
        # An AWS managed CMK is created automatically when you first create
        # an encrypted resource using an AWS service integrated with KMS.
        kms = kms_backends[self.region_name]
        ebs_alias = "alias/aws/ebs"
        if not kms.alias_exists(ebs_alias):
            key = kms.create_key(
                policy="",
                key_usage="ENCRYPT_DECRYPT",
                customer_master_key_spec="SYMMETRIC_DEFAULT",
                description="Default master key that protects my EBS volumes when no other key is defined",
                tags=None,
                region=self.region_name,
            )
            kms.add_alias(key.id, ebs_alias)
        ebs_key = kms.describe_key(ebs_alias)
        return ebs_key.arn
