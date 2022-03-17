import json
from urllib.parse import urlparse

from moto.core.responses import BaseResponse
from moto.core.utils import amzn_request_id
from .models import databrew_backends


class DataBrewResponse(BaseResponse):
    SERVICE_NAME = "databrew"

    @property
    def databrew_backend(self):
        """Return backend instance specific for this region."""
        return databrew_backends[self.region]

    @property
    def parameters(self):
        return json.loads(self.body)

    @amzn_request_id
    def create_recipe(self):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipe.html
        recipe_description = self.parameters.get("Description")
        recipe_steps = self.parameters.get("Steps")
        recipe_name = self.parameters.get("Name")
        tags = self.parameters.get("Tags")
        return json.dumps(
            self.databrew_backend.create_recipe(
                recipe_name, recipe_description, recipe_steps, tags
            ).as_dict()
        )

    @amzn_request_id
    def list_recipes(self):
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRecipes.html
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        recipe_list, next_token = self.databrew_backend.list_recipes(
            next_token=next_token, max_results=max_results
        )
        return json.dumps(
            {
                "Recipes": [recipe.as_dict() for recipe in recipe_list],
                "NextToken": next_token,
            }
        )

    @amzn_request_id
    def describe_recipe_response(self, request, full_url, headers):
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        recipe_name = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        recipe = self.databrew_backend.get_recipe(recipe_name)
        return json.dumps(recipe.as_dict())
