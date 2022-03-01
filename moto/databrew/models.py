from collections import OrderedDict
from datetime import datetime

from moto.core import BaseBackend
from moto.core import BaseModel
from moto.utilities.paginator import paginate

from .exceptions import RecipeAlreadyExistsException
from .exceptions import RecipeNotFoundException


class DataBrewBackend(BaseBackend):
    PAGINATION_MODEL = {
        "list_recipes": {
            "input_token": "next_token",
            "limit_key": "max_results",
            "limit_default": 100,
            "unique_attribute": "name",
        },
    }

    def __init__(self):
        self.recipes = OrderedDict()

    def create_recipe(self, recipe_name, recipe_description, recipe_steps, tags):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipe.html
        if recipe_name in self.recipes:
            raise RecipeAlreadyExistsException()

        recipe = FakeRecipe(recipe_name, recipe_description, recipe_steps, tags)
        self.recipes[recipe_name] = recipe
        return recipe

    @paginate(pagination_model=PAGINATION_MODEL)
    def list_recipes(self):
        return [self.recipes[key] for key in self.recipes] if self.recipes else []

    def get_recipe(self, recipe_name, version):
        if recipe_name not in self.recipes:
            raise RecipeNotFoundException(recipe_name)
        return self.recipes[recipe_name]


class FakeRecipe(BaseModel):
    def __init__(self, recipe_name, recipe_description, recipe_steps, tags):
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


databrew_backend = DataBrewBackend()
