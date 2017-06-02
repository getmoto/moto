from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class AmazonDevPay(BaseResponse):

    def confirm_product_instance(self):
        raise NotImplementedError(
            'AmazonDevPay.confirm_product_instance is not yet implemented')
