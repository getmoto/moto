from datetime import datetime
from typing import Any


class BlockDeviceType:
    """
    Represents parameters for a block device.
    """

    def __init__(
        self,
        ephemeral_name: str | None = None,
        no_device: bool | str = False,
        volume_id: str | None = None,
        snapshot_id: str | None = None,
        status: str | None = None,
        attach_time: datetime | None = None,
        delete_on_termination: bool = False,
        size: int | None = None,
        volume_type: str | None = None,
        iops: str | None = None,
        encrypted: str | None = None,
    ):
        self.ephemeral_name = ephemeral_name
        self.no_device = no_device
        self.volume_id = volume_id
        self.snapshot_id = snapshot_id
        self.status = status
        self.attach_time = attach_time
        self.delete_on_termination = delete_on_termination
        self.size = size
        self.volume_type = volume_type
        self.iops = iops
        self.encrypted = encrypted
        self.kms_key_id = None
        self.throughput = None


class BlockDeviceMapping(dict[Any, Any]):
    """
    Represents a collection of BlockDeviceTypes when creating ec2 instances.

    Example:
    dev_sda1 = BlockDeviceType()
    dev_sda1.size = 100   # change root volume to 100GB instead of default
    bdm = BlockDeviceMapping()
    bdm['/dev/sda1'] = dev_sda1
    reservation = image.run(..., block_device_map=bdm, ...)
    """

    def to_source_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "DeviceName": device_name,
                "Ebs": {
                    "DeleteOnTermination": block.delete_on_termination,
                    "Encrypted": block.encrypted,
                    "VolumeType": block.volume_type,
                    "VolumeSize": block.size,
                },
                "VirtualName": block.ephemeral_name,
            }
            for device_name, block in self.items()
        ]
