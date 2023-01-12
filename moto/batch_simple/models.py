from ..batch.models import (
    batch_backends,
    BaseBackend,
    Job,
    ClientException,
    BatchBackend,
)
from ..core import BackendDict

import datetime
from typing import Any, Dict, List, Tuple, Optional


class BatchSimpleBackend(BaseBackend):
    """
    Implements a Batch-Backend that does not use Docker containers. Submitted Jobs are simply marked as Success
    Annotate your tests with `@mock_batch_simple`-decorator to use this Batch-implementation.
    """

    @property
    def backend(self) -> BatchBackend:
        return batch_backends[self.account_id][self.region_name]

    def __getattribute__(self, name: str) -> Any:
        """
        Magic part that makes this class behave like a wrapper around the regular batch_backend
        We intercept calls to `submit_job` and replace this with our own (non-Docker) implementation
        Every other method call is send through to batch_backend
        """
        if name in [
            "backend",
            "account_id",
            "region_name",
            "urls",
            "_url_module",
            "__class__",
            "url_bases",
        ]:
            return object.__getattribute__(self, name)
        if name in ["submit_job"]:

            def newfunc(*args: Any, **kwargs: Any) -> Any:
                attr = object.__getattribute__(self, name)
                return attr(*args, **kwargs)

            return newfunc
        else:
            return object.__getattribute__(self.backend, name)

    def submit_job(
        self,
        job_name: str,
        job_def_id: str,
        job_queue: str,
        depends_on: Optional[List[Dict[str, str]]] = None,
        container_overrides: Optional[Dict[str, Any]] = None,
        timeout: Optional[Dict[str, int]] = None,
    ) -> Tuple[str, str]:
        # Look for job definition
        job_def = self.get_job_definition(job_def_id)
        if job_def is None:
            raise ClientException(f"Job definition {job_def_id} does not exist")

        queue = self.get_job_queue(job_queue)
        if queue is None:
            raise ClientException(f"Job queue {job_queue} does not exist")

        job = Job(
            job_name,
            job_def,
            queue,
            log_backend=self.logs_backend,
            container_overrides=container_overrides,
            depends_on=depends_on,
            all_jobs=self._jobs,
            timeout=timeout,
        )
        self.backend._jobs[job.job_id] = job

        # We don't want to actually run the job - just mark it as succeeded
        job.job_started_at = datetime.datetime.now()
        job.log_stream_name = job._stream_name
        job._start_attempt()
        job._mark_stopped(success=True)

        return job_name, job.job_id


batch_simple_backends = BackendDict(BatchSimpleBackend, "batch")
