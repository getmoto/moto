from .responses import DataBrewResponse

url_bases = [r"https?://databrew\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/recipeVersions$": DataBrewResponse().list_recipe_versions,
    "{0}/recipes$": DataBrewResponse.dispatch,
    "{0}/recipes/(?P<recipe_name>[^/]+)$": DataBrewResponse().recipe_response,
    "{0}/recipes/(?P<recipe_name>[^/]+)/recipeVersion/(?P<recipe_version>[^/]+)": DataBrewResponse().delete_recipe_version,
    "{0}/recipes/(?P<recipe_name>[^/]+)/publishRecipe$": DataBrewResponse().publish_recipe,
    "{0}/rulesets$": DataBrewResponse.dispatch,
    "{0}/rulesets/(?P<ruleset_name>[^/]+)$": DataBrewResponse().ruleset_response,
    "{0}/datasets$": DataBrewResponse.dispatch,
    "{0}/datasets/(?P<dataset_name>[^/]+)$": DataBrewResponse().dataset_response,
}
