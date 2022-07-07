"""Handles incoming ce requests, invokes methods, returns responses."""
import json

from moto.core.responses import BaseResponse
from .models import ce_backends


class CostExplorerResponse(BaseResponse):
    """Handler for CostExplorer requests and responses."""

    @property
    def ce_backend(self):
        """Return backend instance specific for this region."""
        return ce_backends[self.current_account]["global"]

    def create_cost_category_definition(self):
        params = json.loads(self.body)
        name = params.get("Name")
        rule_version = params.get("RuleVersion")
        rules = params.get("Rules")
        default_value = params.get("DefaultValue")
        split_charge_rules = params.get("SplitChargeRules")
        (
            cost_category_arn,
            effective_start,
        ) = self.ce_backend.create_cost_category_definition(
            name=name,
            rule_version=rule_version,
            rules=rules,
            default_value=default_value,
            split_charge_rules=split_charge_rules,
        )
        return json.dumps(
            dict(CostCategoryArn=cost_category_arn, EffectiveStart=effective_start)
        )

    def describe_cost_category_definition(self):
        params = json.loads(self.body)
        cost_category_arn = params.get("CostCategoryArn")
        cost_category = self.ce_backend.describe_cost_category_definition(
            cost_category_arn=cost_category_arn
        )
        return json.dumps(dict(CostCategory=cost_category.to_json()))

    def delete_cost_category_definition(self):
        params = json.loads(self.body)
        cost_category_arn = params.get("CostCategoryArn")
        (
            cost_category_arn,
            effective_end,
        ) = self.ce_backend.delete_cost_category_definition(
            cost_category_arn=cost_category_arn,
        )
        return json.dumps(
            dict(CostCategoryArn=cost_category_arn, EffectiveEnd=effective_end)
        )

    def update_cost_category_definition(self):
        params = json.loads(self.body)
        cost_category_arn = params.get("CostCategoryArn")
        rule_version = params.get("RuleVersion")
        rules = params.get("Rules")
        default_value = params.get("DefaultValue")
        split_charge_rules = params.get("SplitChargeRules")
        (
            cost_category_arn,
            effective_start,
        ) = self.ce_backend.update_cost_category_definition(
            cost_category_arn=cost_category_arn,
            rule_version=rule_version,
            rules=rules,
            default_value=default_value,
            split_charge_rules=split_charge_rules,
        )
        return json.dumps(
            dict(CostCategoryArn=cost_category_arn, EffectiveStart=effective_start)
        )
