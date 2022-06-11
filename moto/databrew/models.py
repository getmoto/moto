from collections import OrderedDict
from copy import deepcopy
import math
from datetime import datetime

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.utilities.paginator import paginate

from .exceptions import (
    AlreadyExistsException,
    ConflictException,
    ValidationException,
    RulesetAlreadyExistsException,
    RulesetNotFoundException,
    ResourceNotFoundException,
)


class DataBrewBackend(BaseBackend):
    PAGINATION_MODEL = {
        "list_recipes": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
        "list_recipe_versions": {
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
        "list_datasets": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
    }

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.recipes = OrderedDict()
        self.rulesets = OrderedDict()
        self.datasets = OrderedDict()

    @staticmethod
    def validate_length(param, param_name, max_length):
        if len(param) > max_length:
            raise ValidationException(
                f"1 validation error detected: Value '{param}' at '{param_name}' failed to "
                f"satisfy constraint: Member must have length less than or equal to {max_length}"
            )

    def create_recipe(self, recipe_name, recipe_description, recipe_steps, tags):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipe.html
        if recipe_name in self.recipes:
            raise ConflictException(f"The recipe {recipe_name} already exists")

        recipe = FakeRecipe(
            self.region_name, recipe_name, recipe_description, recipe_steps, tags
        )
        self.recipes[recipe_name] = recipe
        return recipe.latest_working

    def delete_recipe_version(self, recipe_name, recipe_version):
        if not FakeRecipe.version_is_valid(recipe_version, latest_published=False):
            raise ValidationException(
                f"Recipe {recipe_name} version {recipe_version} is invalid."
            )

        try:
            recipe = self.recipes[recipe_name]
        except KeyError:
            raise ResourceNotFoundException(f"The recipe {recipe_name} wasn't found")

        if (
            recipe_version != FakeRecipe.LATEST_WORKING
            and float(recipe_version) not in recipe.versions
        ):
            raise ResourceNotFoundException(
                f"The recipe {recipe_name} version {recipe_version } wasn't found."
            )

        if recipe_version in (
            FakeRecipe.LATEST_WORKING,
            str(recipe.latest_working.version),
        ):
            if recipe.latest_published is not None:
                # Can only delete latest working version when there are no others
                raise ValidationException(
                    f"Recipe version {recipe_version} is not allowed to be deleted"
                )
            else:
                del self.recipes[recipe_name]
        else:
            recipe.delete_published_version(recipe_version)

    def update_recipe(self, recipe_name, recipe_description, recipe_steps):
        if recipe_name not in self.recipes:
            raise ResourceNotFoundException(f"The recipe {recipe_name} wasn't found")

        recipe = self.recipes[recipe_name]
        recipe.update(recipe_description, recipe_steps)

        return recipe.latest_working

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_recipes(self, recipe_version=None):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRecipes.html
        if recipe_version == FakeRecipe.LATEST_WORKING:
            version = "latest_working"
        elif recipe_version in (None, FakeRecipe.LATEST_PUBLISHED):
            version = "latest_published"
        else:
            raise ValidationException(
                f"Invalid version {recipe_version}. "
                "Valid versions are LATEST_PUBLISHED and LATEST_WORKING."
            )
        recipes = [getattr(self.recipes[key], version) for key in self.recipes]
        return [r for r in recipes if r is not None]

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_recipe_versions(self, recipe_name):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRecipeVersions.html
        self.validate_length(recipe_name, "name", 255)

        recipe = self.recipes.get(recipe_name)
        if recipe is None:
            return []

        latest_working = recipe.latest_working

        recipe_versions = [
            recipe_version
            for recipe_version in recipe.versions.values()
            if recipe_version is not latest_working
        ]
        return [r for r in recipe_versions if r is not None]

    def get_recipe(self, recipe_name, recipe_version=None):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_DescribeRecipe.html
        self.validate_length(recipe_name, "name", 255)

        if recipe_version is None:
            recipe_version = FakeRecipe.LATEST_PUBLISHED
        else:
            self.validate_length(recipe_version, "recipeVersion", 16)
            if not FakeRecipe.version_is_valid(recipe_version):
                raise ValidationException(
                    f"Recipe {recipe_name} version {recipe_version} isn't valid."
                )

        recipe = None
        if recipe_name in self.recipes:
            if recipe_version == FakeRecipe.LATEST_PUBLISHED:
                recipe = self.recipes[recipe_name].latest_published
            elif recipe_version == FakeRecipe.LATEST_WORKING:
                recipe = self.recipes[recipe_name].latest_working
            else:
                recipe = self.recipes[recipe_name].versions.get(float(recipe_version))
        if recipe is None:
            raise ResourceNotFoundException(
                f"The recipe {recipe_name} for version {recipe_version} wasn't found."
            )
        return recipe

    def publish_recipe(self, recipe_name, description=None):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_PublishRecipe.html
        self.validate_length(recipe_name, "name", 255)
        try:
            self.recipes[recipe_name].publish(description)
        except KeyError:
            raise ResourceNotFoundException(f"Recipe {recipe_name} wasn't found")

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

    def create_dataset(
        self,
        dataset_name,
        dataset_format,
        dataset_format_options,
        dataset_input,
        dataset_path_options,
        tags,
    ):
        if dataset_name in self.datasets:
            raise AlreadyExistsException(dataset_name)

        dataset = FakeDataset(
            self.region_name,
            dataset_name,
            dataset_format,
            dataset_format_options,
            dataset_input,
            dataset_path_options,
            tags,
        )
        self.datasets[dataset_name] = dataset
        return dataset

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_datasets(self):
        return list(self.datasets.values())

    def update_dataset(
        self,
        dataset_name,
        dataset_format,
        dataset_format_options,
        dataset_input,
        dataset_path_options,
        tags,
    ):

        if dataset_name not in self.datasets:
            raise ResourceNotFoundException("One or more resources can't be found.")

        dataset = self.datasets[dataset_name]

        if dataset_format is not None:
            dataset.format = dataset_format
        if dataset_format_options is not None:
            dataset.format_options = dataset_format_options
        if dataset_input is not None:
            dataset.input = dataset_input
        if dataset_path_options is not None:
            dataset.path_options = dataset_path_options
        if tags is not None:
            dataset.tags = tags

        return dataset

    def delete_dataset(self, dataset_name):
        if dataset_name not in self.datasets:
            raise ResourceNotFoundException("One or more resources can't be found.")

        del self.datasets[dataset_name]

    def describe_dataset(self, dataset_name):
        if dataset_name not in self.datasets:
            raise ResourceNotFoundException("One or more resources can't be found.")

        return self.datasets[dataset_name]


class FakeRecipe(BaseModel):
    INITIAL_VERSION = 0.1
    LATEST_WORKING = "LATEST_WORKING"
    LATEST_PUBLISHED = "LATEST_PUBLISHED"

    @classmethod
    def version_is_valid(cls, version, latest_working=True, latest_published=True):
        validity = True

        if len(version) < 1 or len(version) > 16:
            validity = False
        else:
            try:
                version = float(version)
            except ValueError:
                if not (
                    (version == cls.LATEST_WORKING and latest_working)
                    or (version == cls.LATEST_PUBLISHED and latest_published)
                ):
                    validity = False
        return validity

    def __init__(
        self, region_name, recipe_name, recipe_description, recipe_steps, tags
    ):
        self.versions = OrderedDict()
        self.versions[self.INITIAL_VERSION] = FakeRecipeVersion(
            region_name,
            recipe_name,
            recipe_description,
            recipe_steps,
            tags,
            version=self.INITIAL_VERSION,
        )
        self.latest_working = self.versions[self.INITIAL_VERSION]
        self.latest_published = None

    def publish(self, description=None):
        self.latest_published = self.latest_working
        self.latest_working = deepcopy(self.latest_working)
        self.latest_published.publish(description)
        del self.versions[self.latest_working.version]
        self.versions[self.latest_published.version] = self.latest_published
        self.latest_working.version = self.latest_published.version + 0.1
        self.versions[self.latest_working.version] = self.latest_working

    def update(self, description, steps):
        if description is not None:
            self.latest_working.description = description
        if steps is not None:
            self.latest_working.steps = steps

    def delete_published_version(self, version):
        version = float(version)
        assert version.is_integer()
        if version == self.latest_published.version:
            prev_version = version - 1.0
            # Iterate back through the published versions until we find one that exists
            while prev_version >= 1.0:
                if prev_version in self.versions:
                    self.latest_published = self.versions[prev_version]
                    break
                prev_version -= 1.0
            else:
                # Didn't find an earlier published version
                self.latest_published = None
        del self.versions[version]


class FakeRecipeVersion(BaseModel):
    def __init__(
        self, region_name, recipe_name, recipe_description, recipe_steps, tags, version
    ):
        self.region_name = region_name
        self.name = recipe_name
        self.description = recipe_description
        self.steps = recipe_steps
        self.created_time = datetime.now()
        self.tags = tags
        self.published_date = None
        self.version = version

    def as_dict(self):
        dict_recipe = {
            "Name": self.name,
            "Steps": self.steps,
            "Description": self.description,
            "CreateDate": "%.3f" % self.created_time.timestamp(),
            "Tags": self.tags or dict(),
            "RecipeVersion": str(self.version),
        }
        if self.published_date is not None:
            dict_recipe["PublishedDate"] = "%.3f" % self.published_date.timestamp()

        return dict_recipe

    def publish(self, description):
        self.version = float(math.ceil(self.version))
        self.published_date = datetime.now()
        if description is not None:
            self.description = description


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


class FakeDataset(BaseModel):
    def __init__(
        self,
        region_name,
        dataset_name,
        dataset_format,
        dataset_format_options,
        dataset_input,
        dataset_path_options,
        tags,
    ):
        self.region_name = region_name
        self.name = dataset_name
        self.format = dataset_format
        self.format_options = dataset_format_options
        self.input = dataset_input
        self.path_options = dataset_path_options
        self.created_time = datetime.now()
        self.tags = tags

    def as_dict(self):
        return {
            "Name": self.name,
            "Format": self.format,
            "FormatOptions": self.format_options,
            "Input": self.input,
            "PathOptions": self.path_options,
            "CreateTime": self.created_time.isoformat(),
            "Tags": self.tags or dict(),
        }


databrew_backends = BackendDict(DataBrewBackend, "databrew")
