from ..batch.responses import BatchResponse
from .models import batch_simple_backends, BatchBackend


class BatchSimpleResponse(BatchResponse):
    @property
    def batch_backend(self) -> BatchBackend:
        """
        :return: Batch Backend
        :rtype: moto.batch.models.BatchBackend
        """
        return batch_simple_backends[self.current_account][self.region]
