from __future__ import unicode_literals

from moto.core.responses import BaseResponse


class IPAddresses(BaseResponse):
    def assign_private_ip_addresses(self):
        if self.is_not_dryrun("AssignPrivateIPAddress"):
            raise NotImplementedError(
                "IPAddresses.assign_private_ip_addresses is not yet implemented"
            )

    def unassign_private_ip_addresses(self):
        if self.is_not_dryrun("UnAssignPrivateIPAddress"):
            raise NotImplementedError(
                "IPAddresses.unassign_private_ip_addresses is not yet implemented"
            )
