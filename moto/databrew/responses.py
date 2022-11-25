import json
from typing import Any, Dict, Union
from urllib.parse import urlparse

from moto.core.common_types import TYPE_RESPONSE
from moto.core.responses import BaseResponse
from moto.utilities.aws_headers import amzn_request_id
from .models import databrew_backends, DataBrewBackend


class DataBrewResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="databrew")

    @property
    def databrew_backend(self) -> DataBrewBackend:
        """Return backend instance specific for this region."""
        return databrew_backends[self.current_account][self.region]

    # region Recipes
    @property
    def parameters(self) -> Dict[str, Any]:  # type: ignore[misc]
        return json.loads(self.body)

    @amzn_request_id
    def create_recipe(self) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipe.html
        recipe_description = self.parameters.get("Description")
        recipe_steps = self.parameters.get("Steps")
        recipe_name = self.parameters.get("Name")
        tags = self.parameters.get("Tags")
        return json.dumps(
            self.databrew_backend.create_recipe(
                recipe_name, recipe_description, recipe_steps, tags  # type: ignore[arg-type]
            ).as_dict()
        )

    @amzn_request_id
    def delete_recipe_version(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return,misc]
        self.setup_class(request, full_url, headers)
        # https://docs.aws.amazon.com/databrew/latest/dg/API_DeleteRecipeVersion.html
        if request.method == "DELETE":
            parsed_url = urlparse(full_url)
            split_path = parsed_url.path.strip("/").split("/")
            recipe_name = split_path[1]
            recipe_version = split_path[3]
            self.databrew_backend.delete_recipe_version(recipe_name, recipe_version)
            return (
                200,
                {},
                json.dumps({"Name": recipe_name, "RecipeVersion": recipe_version}),
            )

    @amzn_request_id
    def list_recipes(self) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRecipes.html
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )
        recipe_version = self._get_param(
            "RecipeVersion", self._get_param("recipeVersion")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        recipe_list, next_token = self.databrew_backend.list_recipes(
            next_token=next_token,
            max_results=max_results,
            recipe_version=recipe_version,
        )
        return json.dumps(
            {
                "Recipes": [recipe.as_dict() for recipe in recipe_list],
                "NextToken": next_token,
            }
        )

    @amzn_request_id
    def list_recipe_versions(self, request: Any, full_url: str, headers: Any) -> str:  # type: ignore[return,misc]
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRecipeVersions.html
        self.setup_class(request, full_url, headers)
        recipe_name = self._get_param("Name", self._get_param("name"))
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        recipe_list, next_token = self.databrew_backend.list_recipe_versions(
            recipe_name=recipe_name, next_token=next_token, max_results=max_results
        )
        return json.dumps(
            {
                "Recipes": [recipe.as_dict() for recipe in recipe_list],
                "NextToken": next_token,
            }
        )

    @amzn_request_id
    def publish_recipe(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[return,misc]
        self.setup_class(request, full_url, headers)
        if request.method == "POST":
            parsed_url = urlparse(full_url)
            recipe_name = parsed_url.path.strip("/").split("/", 2)[1]
            recipe_description = self.parameters.get("Description")
            self.databrew_backend.publish_recipe(recipe_name, recipe_description)
            return 200, {}, json.dumps({"Name": recipe_name})

    def put_recipe_response(self, recipe_name: str) -> TYPE_RESPONSE:
        recipe_description = self.parameters.get("Description")
        recipe_steps = self.parameters.get("Steps")

        self.databrew_backend.update_recipe(
            recipe_name, recipe_description, recipe_steps  # type: ignore[arg-type]
        )
        return 200, {}, json.dumps({"Name": recipe_name})

    def get_recipe_response(self, recipe_name: str) -> TYPE_RESPONSE:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_DescribeRecipe.html
        recipe_version = self._get_param(
            "RecipeVersion", self._get_param("recipeVersion")
        )
        recipe = self.databrew_backend.describe_recipe(
            recipe_name, recipe_version=recipe_version
        )
        return 200, {}, json.dumps(recipe.as_dict())

    @amzn_request_id
    def recipe_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        recipe_name = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "PUT":
            return self.put_recipe_response(recipe_name)
        elif request.method == "GET":
            return self.get_recipe_response(recipe_name)

    # endregion

    # region Rulesets

    @amzn_request_id
    def create_ruleset(self) -> str:
        ruleset_description = self.parameters.get("Description")
        ruleset_rules = self.parameters.get("Rules")
        ruleset_name = self.parameters.get("Name")
        ruleset_target_arn = self.parameters.get("TargetArn")
        tags = self.parameters.get("Tags")

        return json.dumps(
            self.databrew_backend.create_ruleset(
                ruleset_name,  # type: ignore[arg-type]
                ruleset_description,  # type: ignore[arg-type]
                ruleset_rules,  # type: ignore[arg-type]
                ruleset_target_arn,  # type: ignore[arg-type]
                tags,  # type: ignore[arg-type]
            ).as_dict()
        )

    def put_ruleset_response(self, ruleset_name: str) -> TYPE_RESPONSE:
        ruleset_description = self.parameters.get("Description")
        ruleset_rules = self.parameters.get("Rules")
        tags = self.parameters.get("Tags")

        ruleset = self.databrew_backend.update_ruleset(
            ruleset_name, ruleset_description, ruleset_rules, tags  # type: ignore[arg-type]
        )
        return 200, {}, json.dumps(ruleset.as_dict())

    def get_ruleset_response(self, ruleset_name: str) -> TYPE_RESPONSE:
        ruleset = self.databrew_backend.describe_ruleset(ruleset_name)
        return 200, {}, json.dumps(ruleset.as_dict())

    def delete_ruleset_response(self, ruleset_name: str) -> TYPE_RESPONSE:
        self.databrew_backend.delete_ruleset(ruleset_name)
        return 200, {}, json.dumps({"Name": ruleset_name})

    @amzn_request_id
    def ruleset_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        ruleset_name = parsed_url.path.split("/")[-1]

        if request.method == "PUT":
            response = self.put_ruleset_response(ruleset_name)
            return response
        elif request.method == "GET":
            return self.get_ruleset_response(ruleset_name)
        elif request.method == "DELETE":
            return self.delete_ruleset_response(ruleset_name)

    @amzn_request_id
    def list_rulesets(self) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListRulesets.html
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        ruleset_list, next_token = self.databrew_backend.list_rulesets(
            next_token=next_token, max_results=max_results
        )
        return json.dumps(
            {
                "Rulesets": [ruleset.as_dict() for ruleset in ruleset_list],
                "NextToken": next_token,
            }
        )

    # endregion

    # region Datasets

    @amzn_request_id
    def create_dataset(self) -> str:
        dataset_name = self.parameters.get("Name")
        dataset_format = self.parameters.get("Format")
        dataset_format_options = self.parameters.get("FormatOptions")
        dataset_input = self.parameters.get("Input")
        dataset_path_otions = self.parameters.get("PathOptions")
        dataset_tags = self.parameters.get("Tags")

        return json.dumps(
            self.databrew_backend.create_dataset(
                dataset_name,  # type: ignore[arg-type]
                dataset_format,  # type: ignore[arg-type]
                dataset_format_options,  # type: ignore[arg-type]
                dataset_input,  # type: ignore[arg-type]
                dataset_path_otions,  # type: ignore[arg-type]
                dataset_tags,  # type: ignore[arg-type]
            ).as_dict()
        )

    @amzn_request_id
    def list_datasets(self) -> str:
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        dataset_list, next_token = self.databrew_backend.list_datasets(
            next_token=next_token, max_results=max_results
        )

        return json.dumps(
            {
                "Datasets": [dataset.as_dict() for dataset in dataset_list],
                "NextToken": next_token,
            }
        )

    @amzn_request_id
    def update_dataset(self, dataset_name: str) -> TYPE_RESPONSE:
        dataset_format = self.parameters.get("Format")
        dataset_format_options = self.parameters.get("FormatOptions")
        dataset_input = self.parameters.get("Input")
        dataset_path_otions = self.parameters.get("PathOptions")
        dataset_tags = self.parameters.get("Tags")

        dataset = self.databrew_backend.update_dataset(
            dataset_name,
            dataset_format,  # type: ignore[arg-type]
            dataset_format_options,  # type: ignore[arg-type]
            dataset_input,  # type: ignore[arg-type]
            dataset_path_otions,  # type: ignore[arg-type]
            dataset_tags,  # type: ignore[arg-type]
        )
        return 200, {}, json.dumps(dataset.as_dict())

    @amzn_request_id
    def delete_dataset(self, dataset_name: str) -> TYPE_RESPONSE:
        self.databrew_backend.delete_dataset(dataset_name)
        return 200, {}, json.dumps({"Name": dataset_name})

    @amzn_request_id
    def describe_dataset(self, dataset_name: str) -> TYPE_RESPONSE:
        dataset = self.databrew_backend.describe_dataset(dataset_name)
        return 200, {}, json.dumps(dataset.as_dict())

    @amzn_request_id
    def dataset_response(self, request: Any, full_url: str, headers: Any) -> Union[str, TYPE_RESPONSE]:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        dataset_name = parsed_url.path.split("/")[-1]

        if request.method == "POST":
            return self.create_dataset()
        elif request.method == "GET" and dataset_name:
            return self.describe_dataset(dataset_name)
        elif request.method == "GET":
            return self.list_datasets()
        elif request.method == "DELETE":
            return self.delete_dataset(dataset_name)
        elif request.method == "PUT":
            return self.update_dataset(dataset_name)

    # endregion

    # region Jobs
    @amzn_request_id
    def list_jobs(self, request: Any, full_url: str, headers: Any) -> str:  # type: ignore[misc,return]
        # https://docs.aws.amazon.com/databrew/latest/dg/API_ListJobs.html
        self.setup_class(request, full_url, headers)
        dataset_name = self._get_param("datasetName")
        project_name = self._get_param("projectName")
        next_token = self._get_param("NextToken", self._get_param("nextToken"))
        max_results = self._get_int_param(
            "MaxResults", self._get_int_param("maxResults")
        )

        # pylint: disable=unexpected-keyword-arg, unbalanced-tuple-unpacking
        job_list, next_token = self.databrew_backend.list_jobs(
            dataset_name=dataset_name,
            project_name=project_name,
            next_token=next_token,
            max_results=max_results,
        )
        return json.dumps(
            {
                "Jobs": [job.as_dict() for job in job_list],
                "NextToken": next_token,
            }
        )

    def get_job_response(self, job_name: str) -> TYPE_RESPONSE:
        job = self.databrew_backend.describe_job(job_name)
        return 200, {}, json.dumps(job.as_dict())

    def delete_job_response(self, job_name: str) -> TYPE_RESPONSE:
        self.databrew_backend.delete_job(job_name)
        return 200, {}, json.dumps({"Name": job_name})

    @amzn_request_id
    def job_response(self, request: Any, full_url: str, headers: Any) -> TYPE_RESPONSE:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        job_name = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "GET":
            return self.get_job_response(job_name)
        elif request.method == "DELETE":
            return self.delete_job_response(job_name)

    @amzn_request_id
    def create_profile_job(self) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateProfileJob.html
        kwargs = {
            "dataset_name": self._get_param("DatasetName"),
            "name": self._get_param("Name"),
            "output_location": self._get_param("OutputLocation"),
            "role_arn": self._get_param("RoleArn"),
            "configuration": self._get_param("Configuration"),
            "encryption_key_arn": self._get_param("EncryptionKeyArn"),
            "encryption_mode": self._get_param("EncryptionMode"),
            "job_sample": self._get_param("JobSample"),
            "log_subscription": self._get_param("LogSubscription"),
            "max_capacity": self._get_int_param("MaxCapacity"),
            "max_retries": self._get_int_param("MaxRetries"),
            "tags": self._get_param("Tags"),
            "timeout": self._get_int_param("Timeout"),
            "validation_configurations": self._get_param("ValidationConfigurations"),
        }
        return json.dumps(self.databrew_backend.create_profile_job(**kwargs).as_dict())

    def update_profile_job_response(self, name: str) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_UpdateProfileJob.html
        kwargs = {
            "name": name,
            "output_location": self._get_param("OutputLocation"),
            "role_arn": self._get_param("RoleArn"),
            "configuration": self._get_param("Configuration"),
            "encryption_key_arn": self._get_param("EncryptionKeyArn"),
            "encryption_mode": self._get_param("EncryptionMode"),
            "job_sample": self._get_param("JobSample"),
            "log_subscription": self._get_param("LogSubscription"),
            "max_capacity": self._get_int_param("MaxCapacity"),
            "max_retries": self._get_int_param("MaxRetries"),
            "timeout": self._get_int_param("Timeout"),
            "validation_configurations": self._get_param("ValidationConfigurations"),
        }
        return json.dumps(self.databrew_backend.update_profile_job(**kwargs).as_dict())

    @amzn_request_id
    def create_recipe_job(self) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_CreateRecipeJob.html
        kwargs = {
            "name": self._get_param("Name"),
            "role_arn": self._get_param("RoleArn"),
            "database_outputs": self._get_param("DatabaseOutputs"),
            "data_catalog_outputs": self._get_param("DataCatalogOutputs"),
            "dataset_name": self._get_param("DatasetName"),
            "encryption_key_arn": self._get_param("EncryptionKeyArn"),
            "encryption_mode": self._get_param("EncryptionMode"),
            "log_subscription": self._get_param("LogSubscription"),
            "max_capacity": self._get_int_param("MaxCapacity"),
            "max_retries": self._get_int_param("MaxRetries"),
            "outputs": self._get_param("Outputs"),
            "project_name": self._get_param("ProjectName"),
            "recipe_reference": self._get_param("RecipeReference"),
            "tags": self._get_param("Tags"),
            "timeout": self._get_int_param("Timeout"),
        }
        return json.dumps(self.databrew_backend.create_recipe_job(**kwargs).as_dict())

    @amzn_request_id
    def update_recipe_job_response(self, name: str) -> str:
        # https://docs.aws.amazon.com/databrew/latest/dg/API_UpdateRecipeJob.html
        kwargs = {
            "name": name,
            "role_arn": self._get_param("RoleArn"),
            "database_outputs": self._get_param("DatabaseOutputs"),
            "data_catalog_outputs": self._get_param("DataCatalogOutputs"),
            "encryption_key_arn": self._get_param("EncryptionKeyArn"),
            "encryption_mode": self._get_param("EncryptionMode"),
            "log_subscription": self._get_param("LogSubscription"),
            "max_capacity": self._get_int_param("MaxCapacity"),
            "max_retries": self._get_int_param("MaxRetries"),
            "outputs": self._get_param("Outputs"),
            "timeout": self._get_int_param("Timeout"),
        }
        return json.dumps(self.databrew_backend.update_recipe_job(**kwargs).as_dict())

    @amzn_request_id
    def profile_job_response(self, request: Any, full_url: str, headers: Any) -> str:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        job_name = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "PUT":
            return self.update_profile_job_response(job_name)

    @amzn_request_id
    def recipe_job_response(self, request: Any, full_url: str, headers: Any) -> str:  # type: ignore[misc,return]
        self.setup_class(request, full_url, headers)
        parsed_url = urlparse(full_url)

        job_name = parsed_url.path.rstrip("/").rsplit("/", 1)[1]

        if request.method == "PUT":
            return self.update_recipe_job_response(job_name)

    # endregion
