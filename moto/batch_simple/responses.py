from ..batch.responses import BatchResponse
from .models import batch_simple_backends


class BatchSimpleResponse(BatchResponse):
    @property
    def batch_backend(self):
        """
        :return: Batch Backend
        :rtype: moto.batch.models.BatchBackend
        """
        return batch_simple_backends[self.region]
