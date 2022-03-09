from .responses import DataBrewResponse

url_bases = [r"https?://databrew\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/recipes$": DataBrewResponse.dispatch,
    "{0}/recipes/(?P<recipe_name>[^/]+)$": DataBrewResponse().describe_recipe_response,
}
