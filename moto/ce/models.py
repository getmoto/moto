"""CostExplorerBackend class with methods for supported APIs."""

from .exceptions import CostCategoryNotFound
from moto.core import BaseBackend, BackendDict, BaseModel
from moto.utilities.tagging_service import TaggingService
from moto.core.utils import iso_8601_datetime_without_milliseconds
from moto.moto_api._internal import mock_random
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional


def first_day() -> str:
    as_date = (
        datetime.today()
        .replace(day=1)
        .replace(hour=0)
        .replace(minute=0)
        .replace(second=0)
    )
    return iso_8601_datetime_without_milliseconds(as_date)  # type: ignore[return-value]


class CostCategoryDefinition(BaseModel):
    def __init__(
        self,
        account_id: str,
        name: str,
        effective_start: Optional[str],
        rule_version: str,
        rules: List[Dict[str, Any]],
        default_value: str,
        split_charge_rules: List[Dict[str, Any]],
    ):
        self.name = name
        self.rule_version = rule_version
        self.rules = rules
        self.default_value = default_value
        self.split_charge_rules = split_charge_rules
        self.arn = f"arn:aws:ce::{account_id}:costcategory/{str(mock_random.uuid4())}"
        self.effective_start: str = effective_start or first_day()

    def update(
        self,
        rule_version: str,
        effective_start: Optional[str],
        rules: List[Dict[str, Any]],
        default_value: str,
        split_charge_rules: List[Dict[str, Any]],
    ) -> None:
        self.rule_version = rule_version
        self.rules = rules
        self.default_value = default_value
        self.split_charge_rules = split_charge_rules
        self.effective_start = effective_start or first_day()

    def to_json(self) -> Dict[str, Any]:
        return {
            "CostCategoryArn": self.arn,
            "Name": self.name,
            "EffectiveStart": self.effective_start,
            "RuleVersion": self.rule_version,
            "Rules": self.rules,
            "DefaultValue": self.default_value,
            "SplitChargeRules": self.split_charge_rules,
        }


class CostExplorerBackend(BaseBackend):
    """Implementation of CostExplorer APIs."""

    def __init__(self, region_name: str, account_id: str):
        super().__init__(region_name, account_id)
        self.cost_categories: Dict[str, CostCategoryDefinition] = dict()
        self.tagger = TaggingService()

    def create_cost_category_definition(
        self,
        name: str,
        effective_start: Optional[str],
        rule_version: str,
        rules: List[Dict[str, Any]],
        default_value: str,
        split_charge_rules: List[Dict[str, Any]],
        tags: List[Dict[str, str]],
    ) -> Tuple[str, str]:
        """
        The EffectiveOn and ResourceTags-parameters are not yet implemented
        """
        ccd = CostCategoryDefinition(
            self.account_id,
            name,
            effective_start,
            rule_version,
            rules,
            default_value,
            split_charge_rules,
        )
        self.cost_categories[ccd.arn] = ccd
        self.tag_resource(ccd.arn, tags)
        return ccd.arn, ccd.effective_start

    def describe_cost_category_definition(
        self, cost_category_arn: str
    ) -> CostCategoryDefinition:
        """
        The EffectiveOn-parameter is not yet implemented
        """
        if cost_category_arn not in self.cost_categories:
            ccd_id = cost_category_arn.split("/")[-1]
            raise CostCategoryNotFound(ccd_id)
        return self.cost_categories[cost_category_arn]

    def delete_cost_category_definition(
        self, cost_category_arn: str
    ) -> Tuple[str, str]:
        """
        The EffectiveOn-parameter is not yet implemented
        """
        self.cost_categories.pop(cost_category_arn, None)
        return cost_category_arn, ""

    def update_cost_category_definition(
        self,
        cost_category_arn: str,
        effective_start: Optional[str],
        rule_version: str,
        rules: List[Dict[str, Any]],
        default_value: str,
        split_charge_rules: List[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """
        The EffectiveOn-parameter is not yet implemented
        """
        cost_category = self.describe_cost_category_definition(cost_category_arn)
        cost_category.update(
            rule_version=rule_version,
            rules=rules,
            default_value=default_value,
            split_charge_rules=split_charge_rules,
            effective_start=effective_start,
        )

        return cost_category_arn, cost_category.effective_start

    def list_tags_for_resource(self, resource_arn: str) -> List[Dict[str, str]]:
        return self.tagger.list_tags_for_resource(arn=resource_arn)["Tags"]

    def tag_resource(self, resource_arn: str, tags: List[Dict[str, str]]) -> None:
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn: str, tag_keys: List[str]) -> None:
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)


ce_backends = BackendDict(
    CostExplorerBackend, "ce", use_boto3_regions=False, additional_regions=["global"]
)
