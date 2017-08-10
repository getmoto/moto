from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class ReservedInstances(BaseResponse):

    def cancel_reserved_instances_listing(self):
        if self.is_not_dryrun('CancelReservedInstances'):
            raise NotImplementedError(
                'ReservedInstances.cancel_reserved_instances_listing is not yet implemented')

    def create_reserved_instances_listing(self):
        if self.is_not_dryrun('CreateReservedInstances'):
            raise NotImplementedError(
                'ReservedInstances.create_reserved_instances_listing is not yet implemented')

    def describe_reserved_instances(self):
        raise NotImplementedError(
            'ReservedInstances.describe_reserved_instances is not yet implemented')

    def describe_reserved_instances_listings(self):
        raise NotImplementedError(
            'ReservedInstances.describe_reserved_instances_listings is not yet implemented')

    def describe_reserved_instances_offerings(self):
        raise NotImplementedError(
            'ReservedInstances.describe_reserved_instances_offerings is not yet implemented')

    def purchase_reserved_instances_offering(self):
        if self.is_not_dryrun('PurchaseReservedInstances'):
            raise NotImplementedError(
                'ReservedInstances.purchase_reserved_instances_offering is not yet implemented')
