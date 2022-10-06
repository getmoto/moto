"""CostExplorerBackend class with methods for supported APIs."""

from .exceptions import CostCategoryNotFound
from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.utilities.tagging_service import TaggingService
from moto.moto_api._internal import mock_random


class CostCategoryDefinition(BaseModel):
    def __init__(
        self, account_id, name, rule_version, rules, default_value, split_charge_rules
    ):
        self.name = name
        self.rule_version = rule_version
        self.rules = rules
        self.default_value = default_value
        self.split_charge_rules = split_charge_rules
        self.arn = f"arn:aws:ce::{account_id}:costcategory/{str(mock_random.uuid4())}"

    def update(self, rule_version, rules, default_value, split_charge_rules):
        self.rule_version = rule_version
        self.rules = rules
        self.default_value = default_value
        self.split_charge_rules = split_charge_rules

    def to_json(self):
        return {
            "CostCategoryArn": self.arn,
            "Name": self.name,
            "RuleVersion": self.rule_version,
            "Rules": self.rules,
            "DefaultValue": self.default_value,
            "SplitChargeRules": self.split_charge_rules,
        }


class CostExplorerBackend(BaseBackend):
    """Implementation of CostExplorer APIs."""

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.cost_categories = dict()
        self.tagger = TaggingService()

    def create_cost_category_definition(
        self,
        name,
        rule_version,
        rules,
        default_value,
        split_charge_rules,
        tags,
    ):
        """
        The EffectiveOn and ResourceTags-parameters are not yet implemented
        """
        ccd = CostCategoryDefinition(
            self.account_id,
            name,
            rule_version,
            rules,
            default_value,
            split_charge_rules,
        )
        self.cost_categories[ccd.arn] = ccd
        self.tag_resource(ccd.arn, tags)
        return ccd.arn, ""

    def describe_cost_category_definition(self, cost_category_arn):
        """
        The EffectiveOn-parameter is not yet implemented
        """
        if cost_category_arn not in self.cost_categories:
            ccd_id = cost_category_arn.split("/")[-1]
            raise CostCategoryNotFound(ccd_id)
        return self.cost_categories[cost_category_arn]

    def delete_cost_category_definition(self, cost_category_arn):
        """
        The EffectiveOn-parameter is not yet implemented
        """
        self.cost_categories.pop(cost_category_arn, None)
        return cost_category_arn, ""

    def update_cost_category_definition(
        self, cost_category_arn, rule_version, rules, default_value, split_charge_rules
    ):
        """
        The EffectiveOn-parameter is not yet implemented
        """
        cost_category = self.describe_cost_category_definition(cost_category_arn)
        cost_category.update(rule_version, rules, default_value, split_charge_rules)

        return cost_category_arn, ""

    def list_tags_for_resource(self, resource_arn):
        return self.tagger.list_tags_for_resource(arn=resource_arn)["Tags"]

    def tag_resource(self, resource_arn, tags):
        self.tagger.tag_resource(resource_arn, tags)

    def untag_resource(self, resource_arn, tag_keys):
        self.tagger.untag_resource_using_names(resource_arn, tag_keys)


ce_backends = BackendDict(
    CostExplorerBackend, "ce", use_boto3_regions=False, additional_regions=["global"]
)
