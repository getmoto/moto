import json

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .models import forecast_backends


class ForecastResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="forecast")

    @property
    def forecast_backend(self):
        return forecast_backends[self.current_account][self.region]

    @amzn_request_id
    def create_dataset_group(self):
        dataset_group_name = self._get_param("DatasetGroupName")
        domain = self._get_param("Domain")
        dataset_arns = self._get_param("DatasetArns")
        tags = self._get_param("Tags")

        dataset_group = self.forecast_backend.create_dataset_group(
            dataset_group_name=dataset_group_name,
            domain=domain,
            dataset_arns=dataset_arns,
            tags=tags,
        )
        response = {"DatasetGroupArn": dataset_group.arn}
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def describe_dataset_group(self):
        dataset_group_arn = self._get_param("DatasetGroupArn")

        dataset_group = self.forecast_backend.describe_dataset_group(
            dataset_group_arn=dataset_group_arn
        )
        response = {
            "CreationTime": dataset_group.creation_date,
            "DatasetArns": dataset_group.dataset_arns,
            "DatasetGroupArn": dataset_group.arn,
            "DatasetGroupName": dataset_group.dataset_group_name,
            "Domain": dataset_group.domain,
            "LastModificationTime": dataset_group.modified_date,
            "Status": "ACTIVE",
        }
        return 200, {}, json.dumps(response)

    @amzn_request_id
    def delete_dataset_group(self):
        dataset_group_arn = self._get_param("DatasetGroupArn")
        self.forecast_backend.delete_dataset_group(dataset_group_arn)
        return 200, {}, None

    @amzn_request_id
    def update_dataset_group(self):
        dataset_group_arn = self._get_param("DatasetGroupArn")
        dataset_arns = self._get_param("DatasetArns")
        self.forecast_backend.update_dataset_group(dataset_group_arn, dataset_arns)
        return 200, {}, None

    @amzn_request_id
    def list_dataset_groups(self):
        list_all = self.forecast_backend.list_dataset_groups()
        list_all = sorted(
            [
                {
                    "DatasetGroupArn": dsg.arn,
                    "DatasetGroupName": dsg.dataset_group_name,
                    "CreationTime": dsg.creation_date,
                    "LastModificationTime": dsg.creation_date,
                }
                for dsg in list_all
            ],
            key=lambda x: x["LastModificationTime"],
            reverse=True,
        )
        response = {"DatasetGroups": list_all}
        return 200, {}, json.dumps(response)
