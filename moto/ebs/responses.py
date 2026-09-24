"""Handles incoming ebs requests, invokes methods, returns responses."""

from typing import Any

from moto.core.responses import ActionResult, BaseResponse

from .models import EBSBackend, ebs_backends


class EBSResponse(BaseResponse):
    """Handler for EBS requests and responses."""

    def __init__(self) -> None:
        super().__init__(service_name="ebs")
        self.automated_parameter_parsing = True

    def setup_class(self, request: Any, full_url: str, headers: Any) -> None:  # type: ignore
        super().setup_class(request, full_url, headers, use_raw_body=True)

    @property
    def ebs_backend(self) -> EBSBackend:
        """Return backend instance specific for this region."""
        return ebs_backends[self.current_account][self.region]

    def start_snapshot(self) -> ActionResult:
        volume_size = self._get_param("VolumeSize")
        tags = self._get_param("Tags")
        description = self._get_param("Description")
        snapshot = self.ebs_backend.start_snapshot(
            volume_size=volume_size,
            tags=tags,
            description=description,
        )
        result = {
            "SnapshotId": snapshot.snapshot_id,
            "OwnerId": snapshot.account_id,
            "Status": snapshot.status,
            "StartTime": snapshot.start_time,
            "VolumeSize": snapshot.volume_size,
            "BlockSize": snapshot.block_size,
            "Tags": snapshot.tags,
            "Description": snapshot.description,
        }
        return ActionResult(result)

    def complete_snapshot(self) -> ActionResult:
        snapshot_id = self._get_param("SnapshotId")
        status = self.ebs_backend.complete_snapshot(snapshot_id=snapshot_id)
        return ActionResult({"Status": status})

    def put_snapshot_block(self) -> ActionResult:
        snapshot_id = self._get_param("SnapshotId")
        block_index = self._get_param("BlockIndex")
        block_data = self._get_param("BlockData")
        checksum = self._get_param("Checksum")
        checksum_algorithm = self._get_param("ChecksumAlgorithm")
        data_length = self._get_param("DataLength")
        checksum, checksum_algorithm = self.ebs_backend.put_snapshot_block(
            snapshot_id=snapshot_id,
            block_index=block_index,
            block_data=block_data,
            checksum=checksum,
            checksum_algorithm=checksum_algorithm,
            data_length=data_length,
        )
        result = {"Checksum": checksum, "ChecksumAlgorithm": checksum_algorithm}
        return ActionResult(result)

    def get_snapshot_block(self) -> ActionResult:
        snapshot_id = self._get_param("SnapshotId")
        block_index = self._get_param("BlockIndex")
        block = self.ebs_backend.get_snapshot_block(
            snapshot_id=snapshot_id,
            block_index=block_index,
        )
        result = {
            "DataLength": block.data_length,
            "BlockData": block.block_data,
            "Checksum": block.checksum,
            "ChecksumAlgorithm": block.checksum_algorithm,
        }
        return ActionResult(result)

    def list_changed_blocks(self) -> ActionResult:
        first_snapshot_id = self._get_param("FirstSnapshotId")
        second_snapshot_id = self._get_param("SecondSnapshotId")
        changed_blocks, snapshot = self.ebs_backend.list_changed_blocks(
            first_snapshot_id=first_snapshot_id,
            second_snapshot_id=second_snapshot_id,
        )
        blocks = [
            {"BlockIndex": idx, "FirstBlockToken": x, "SecondBlockToken": y}
            for idx, (x, y) in changed_blocks.items()
        ]
        result = {
            "ChangedBlocks": blocks,
            "VolumeSize": snapshot.volume_size,
            "BlockSize": snapshot.block_size,
        }
        return ActionResult(result)

    def list_snapshot_blocks(self) -> ActionResult:
        snapshot_id = self._get_param("SnapshotId")
        snapshot = self.ebs_backend.list_snapshot_blocks(
            snapshot_id=snapshot_id,
        )
        blocks = [
            {"BlockIndex": idx, "BlockToken": b.block_token}
            for idx, b in snapshot.blocks.items()
        ]
        result = {
            "Blocks": blocks,
            "VolumeSize": snapshot.volume_size,
            "BlockSize": snapshot.block_size,
        }
        return ActionResult(result)
