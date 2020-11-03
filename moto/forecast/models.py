from future.utils import iteritems
import re
from datetime import datetime
from enum import Enum


from boto3 import Session

from moto.core import ACCOUNT_ID, BaseBackend
from moto.core.utils import iso_8601_datetime_without_milliseconds
from .exceptions import (
    InvalidInputException,
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ValidationException,
)


class Domain(Enum):
    RETAIL = 1
    CUSTOM = 2
    INVENTORY_PLANNING = 3
    EC2_CAPACITY = 4
    WORK_FORCE = 5
    WEB_TRAFFIC = 6
    METRICS = 7


class DatasetGroup:
    accepted_dataset_group_name_format = re.compile(r"^[a-zA-Z][a-z-A-Z0-9_]*")
    accepted_dataset_group_arn_format = re.compile(r"^[a-zA-Z0-9\-\_\.\/\:]+$")
    accepted_dataset_types = [
        "INVENTORY_PLANNING",
        "METRICS",
        "RETAIL",
        "EC2_CAPACITY",
        "CUSTOM",
        "WEB_TRAFFIC",
        "WORK_FORCE",
    ]

    def __init__(
        self, region_name, dataset_arns, dataset_group_name, domain, tags=None
    ):
        self.creation_date = iso_8601_datetime_without_milliseconds(datetime.now())
        self.modified_date = self.creation_date

        self.arn = (
            "arn:aws:forecast:"
            + region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":dataset-group/"
            + dataset_group_name
        )
        self.dataset_arns = dataset_arns if dataset_arns else []
        self.dataset_group_name = dataset_group_name
        self.domain = domain
        self.tags = tags
        self._validate()

    def update(self, dataset_arns):
        self.dataset_arns = dataset_arns
        self.last_modified_date = iso_8601_datetime_without_milliseconds(datetime.now())

    def _validate(self):
        errors = []

        self._update_validation_errors(errors, self._validate_dataset_group_name())
        self._update_validation_errors(errors, self._validate_dataset_group_name_len())
        self._update_validation_errors(errors, self._validate_dataset_group_domain())
        if errors:
            err_count = len(errors)
            message = (
                str(err_count) + " validation error" + "s"
                if err_count > 1
                else "" + ": " + "; ".join(errors)
            )
            raise ValidationException(message)

    def _update_validation_errors(self, errors, result):
        if result:
            errors.append(result)

    def _validate_dataset_group_name(self):
        if re.match(self.accepted_dataset_group_name_format, self.dataset_group_name):
            return None
        return (
            "Value "
            + self.dataset_group_name
            + " at 'datasetGroupName' failed to satisfy constraint: Member must satisfy regular expression pattern "
            + self.accepted_dataset_group_name_format.pattern
        )

    def _validate_dataset_group_name_len(self):
        if len(self.dataset_group_name) < 64:
            return None
        return (
            "Value '"
            + self.dataset_group_name
            + "' at 'datasetGroupName' failed to satisfy constraint: Member must have length less than or equal to 63"
        )

    def _validate_dataset_group_domain(self):
        if self.domain not in self.accepted_dataset_types:
            return (
                "Value '"
                + self.domain
                + " at 'domain' failed to satisfy constraint: Member must satisfy enum value set "
                + str(self.accepted_dataset_types)
            )


class ForecastBackend(BaseBackend):
    def __init__(self, region_name):
        super(ForecastBackend, self).__init__()
        self.dataset_groups = {}
        self.datasets = {}
        self.region_name = region_name

    def create_dataset_group(self, dataset_group_name, domain, dataset_arns, tags):
        dataset_group = DatasetGroup(
            region_name=self.region_name,
            dataset_group_name=dataset_group_name,
            domain=domain,
            dataset_arns=dataset_arns,
            tags=tags,
        )

        if dataset_arns:
            for dataset_arn in dataset_arns:
                if dataset_arn not in self.datasets:
                    raise InvalidInputException(
                        "Dataset arns: [" + dataset_arn + "] are not found"
                    )

        if self.dataset_groups.get(dataset_group.arn):
            raise ResourceAlreadyExistsException(
                "A dataset group already exists with the arn: " + dataset_group.arn
            )

        self.dataset_groups[dataset_group.arn] = dataset_group
        return dataset_group

    def describe_dataset_group(self, dataset_group_arn):
        try:
            dataset_group = self.dataset_groups[dataset_group_arn]
        except KeyError:
            raise ResourceNotFoundException("No resource found " + dataset_group_arn)
        return dataset_group

    def delete_dataset_group(self, dataset_group_arn):
        try:
            del self.dataset_groups[dataset_group_arn]
        except KeyError:
            raise ResourceNotFoundException("No resource found " + dataset_group_arn)

    def update_dataset_group(self, dataset_group_arn, dataset_arns):
        try:
            dsg = self.dataset_groups[dataset_group_arn]
        except KeyError:
            raise ResourceNotFoundException("No resource found " + dataset_group_arn)

        for dataset_arn in dataset_arns:
            if dataset_arn not in dsg.dataset_arns:
                raise InvalidInputException(
                    "Dataset arns: [" + dataset_arn + "] are not found"
                )

        dsg.update(dataset_arns)

    def list_dataset_groups(self):
        return [v for (_, v) in iteritems(self.dataset_groups)]

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)


forecast_backends = {}
for region in Session().get_available_regions("forecast"):
    forecast_backends[region] = ForecastBackend(region)
