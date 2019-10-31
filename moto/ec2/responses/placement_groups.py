from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class PlacementGroups(BaseResponse):
    def create_placement_group(self):
        if self.is_not_dryrun("CreatePlacementGroup"):
            raise NotImplementedError(
                "PlacementGroups.create_placement_group is not yet implemented"
            )

    def delete_placement_group(self):
        if self.is_not_dryrun("DeletePlacementGroup"):
            raise NotImplementedError(
                "PlacementGroups.delete_placement_group is not yet implemented"
            )

    def describe_placement_groups(self):
        raise NotImplementedError(
            "PlacementGroups.describe_placement_groups is not yet implemented"
        )
