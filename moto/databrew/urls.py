from .responses import DataBrewResponse

url_bases = [r"https?://databrew\.(.+)\.amazonaws.com"]

url_paths = {
    "{0}/recipeVersions$": DataBrewResponse.method_dispatch(
        DataBrewResponse.list_recipe_versions
    ),
    "{0}/recipes$": DataBrewResponse.dispatch,
    "{0}/recipes/(?P<recipe_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.recipe_response
    ),
    "{0}/recipes/(?P<recipe_name>[^/]+)/recipeVersion/(?P<recipe_version>[^/]+)": DataBrewResponse.method_dispatch(
        DataBrewResponse.delete_recipe_version
    ),
    "{0}/recipes/(?P<recipe_name>[^/]+)/publishRecipe$": DataBrewResponse.method_dispatch(
        DataBrewResponse.publish_recipe
    ),
    "{0}/rulesets$": DataBrewResponse.dispatch,
    "{0}/rulesets/(?P<ruleset_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.ruleset_response
    ),
    "{0}/datasets$": DataBrewResponse.dispatch,
    "{0}/datasets/(?P<dataset_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.dataset_response
    ),
    "{0}/jobs$": DataBrewResponse.method_dispatch(DataBrewResponse.list_jobs),
    "{0}/jobs/(?P<job_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.job_response
    ),
    "{0}/profileJobs$": DataBrewResponse.dispatch,
    "{0}/recipeJobs$": DataBrewResponse.dispatch,
    "{0}/profileJobs/(?P<job_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.profile_job_response
    ),
    "{0}/recipeJobs/(?P<job_name>[^/]+)$": DataBrewResponse.method_dispatch(
        DataBrewResponse.recipe_job_response
    ),
}
