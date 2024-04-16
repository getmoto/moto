"""SageMakerMetricsBackend class with methods for supported APIs."""
from datetime import datetime
from typing import List, Dict, Union

from moto.core.base_backend import BaseBackend, BackendDict
from moto.sagemaker import sagemaker_backends


class SageMakerMetricsBackend(BaseBackend):
    """Implementation of SageMakerMetrics APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.sagemaker_backend = sagemaker_backends[account_id][region_name]

    def batch_put_metrics(
            self,
            trial_component_name: str,
            metric_data: List[Dict[str, Union[str, int, float, datetime]]],
    ):
        if trial_component_name not in self.sagemaker_backend.trial_components:
            return {
                "Errors": [{'Code': 'VALIDATION_ERROR', 'MetricIndex': 0}]
            }
        trial_component = self.sagemaker_backend.trial_components[trial_component_name]
        trial_component.metrics.extend(metric_data)
        return {}
    

sagemakermetrics_backends = BackendDict(SageMakerMetricsBackend, "sagemaker-metrics")
