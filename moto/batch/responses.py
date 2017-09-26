from __future__ import unicode_literals
from moto.core.responses import BaseResponse
from .models import batch_backends


class BatchResponse(BaseResponse):
    @property
    def batch_backend(self):
        return batch_backends[self.region]

    # add methods from here


# add teampltes from here
