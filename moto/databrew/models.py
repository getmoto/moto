from collections import OrderedDict
from datetime import datetime

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.utilities.paginator import paginate
from .exceptions import RecipeAlreadyExistsException, RecipeNotFoundException
from .exceptions import RulesetAlreadyExistsException, RulesetNotFoundException


class DataBrewBackend(BaseBackend):
    PAGINATION_MODEL = {
        "list_recipes": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
        "list_rulesets": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
    }

    def __init__(self, region_name):
        self.region_name = region_name
        self.recipes = OrderedDict()
        self.rulesets = OrderedDict()

    def reset(self):
        """Re-initialize all attributes for this instance."""
        region_name = self.region_name
        self.__init__(region_name)

    def create_recipe(self, recipe_name, recipe_description, recipe_steps, tags):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipe.html
        if recipe_name in self.recipes:
            raise RecipeAlreadyExistsException()

        recipe = FakeRecipe(
            self.region_name, recipe_name, recipe_description, recipe_steps, tags
        )
        self.recipes[recipe_name] = recipe
        return recipe

    def update_recipe(self, recipe_name, recipe_description, recipe_steps, tags):
        if recipe_name not in self.recipes:
            raise RecipeNotFoundException(recipe_name)

        recipe = self.recipes[recipe_name]
        if recipe_description is not None:
            recipe.description = recipe_description
        if recipe_steps is not None:
            recipe.steps = recipe_steps
        if tags is not None:
            recipe.tags = tags

        return recipe

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_recipes(self):
        return [self.recipes[key] for key in self.recipes] if self.recipes else []

    def get_recipe(self, recipe_name):
        """
        The Version-parameter has not yet been implemented
        """
        if recipe_name not in self.recipes:
            raise RecipeNotFoundException(recipe_name)
        return self.recipes[recipe_name]

    def create_ruleset(
        self, ruleset_name, ruleset_description, ruleset_rules, ruleset_target_arn, tags
    ):
        if ruleset_name in self.rulesets:
            raise RulesetAlreadyExistsException()

        ruleset = FakeRuleset(
            self.region_name,
            ruleset_name,
            ruleset_description,
            ruleset_rules,
            ruleset_target_arn,
            tags,
        )
        self.rulesets[ruleset_name] = ruleset
        return ruleset

    def update_ruleset(self, ruleset_name, ruleset_description, ruleset_rules, tags):
        if ruleset_name not in self.rulesets:
            raise RulesetNotFoundException(ruleset_name)

        ruleset = self.rulesets[ruleset_name]
        if ruleset_description is not None:
            ruleset.description = ruleset_description
        if ruleset_rules is not None:
            ruleset.rules = ruleset_rules
        if tags is not None:
            ruleset.tags = tags

        return ruleset

    def get_ruleset(self, ruleset_name):
        if ruleset_name not in self.rulesets:
            raise RulesetNotFoundException(ruleset_name)
        return self.rulesets[ruleset_name]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_rulesets(self):
        return list(self.rulesets.values())

    def delete_ruleset(self, ruleset_name):
        if ruleset_name not in self.rulesets:
            raise RulesetNotFoundException(ruleset_name)

        del self.rulesets[ruleset_name]


class FakeRecipe(BaseModel):
    def __init__(
        self, region_name, recipe_name, recipe_description, recipe_steps, tags
    ):
        self.region_name = region_name
        self.name = recipe_name
        self.description = recipe_description
        self.steps = recipe_steps
        self.created_time = datetime.now()
        self.tags = tags

    def as_dict(self):
        return {
            "Name": self.name,
            "Steps": self.steps,
            "Description": self.description,
            "CreateTime": self.created_time.isoformat(),
            "Tags": self.tags or dict(),
        }


class FakeRuleset(BaseModel):
    def __init__(
        self,
        region_name,
        ruleset_name,
        ruleset_description,
        ruleset_rules,
        ruleset_target_arn,
        tags,
    ):
        self.region_name = region_name
        self.name = ruleset_name
        self.description = ruleset_description
        self.rules = ruleset_rules
        self.target_arn = ruleset_target_arn
        self.created_time = datetime.now()

        self.tags = tags

    def as_dict(self):
        return {
            "Name": self.name,
            "Rules": self.rules,
            "Description": self.description,
            "TargetArn": self.target_arn,
            "CreateTime": self.created_time.isoformat(),
            "Tags": self.tags or dict(),
        }


databrew_backends = BackendDict(DataBrewBackend, "databrew")
