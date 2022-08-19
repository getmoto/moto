import json

from moto.core.responses import BaseResponse
from .exceptions import (
    PartitionAlreadyExistsException,
    PartitionNotFoundException,
    TableNotFoundException,
)
from .models import glue_backends


class GlueResponse(BaseResponse):
    def __init__(self):
        super().__init__(service_name="glue")

    @property
    def glue_backend(self):
        return glue_backends[self.current_account]["global"]

    @property
    def parameters(self):
        return json.loads(self.body)

    def create_database(self):
        database_input = self.parameters.get("DatabaseInput")
        database_name = database_input.get("Name")
        if "CatalogId" in self.parameters:
            database_input["CatalogId"] = self.parameters.get("CatalogId")
        self.glue_backend.create_database(database_name, database_input)
        return ""

    def get_database(self):
        database_name = self.parameters.get("Name")
        database = self.glue_backend.get_database(database_name)
        return json.dumps({"Database": database.as_dict()})

    def get_databases(self):
        database_list = self.glue_backend.get_databases()
        return json.dumps(
            {"DatabaseList": [database.as_dict() for database in database_list]}
        )

    def update_database(self):
        database_input = self.parameters.get("DatabaseInput")
        database_name = self.parameters.get("Name")
        if "CatalogId" in self.parameters:
            database_input["CatalogId"] = self.parameters.get("CatalogId")
        self.glue_backend.update_database(database_name, database_input)
        return ""

    def delete_database(self):
        name = self.parameters.get("Name")
        self.glue_backend.delete_database(name)
        return json.dumps({})

    def create_table(self):
        database_name = self.parameters.get("DatabaseName")
        table_input = self.parameters.get("TableInput")
        table_name = table_input.get("Name")
        self.glue_backend.create_table(database_name, table_name, table_input)
        return ""

    def get_table(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("Name")
        table = self.glue_backend.get_table(database_name, table_name)

        return json.dumps({"Table": table.as_dict()})

    def update_table(self):
        database_name = self.parameters.get("DatabaseName")
        table_input = self.parameters.get("TableInput")
        table_name = table_input.get("Name")
        table = self.glue_backend.get_table(database_name, table_name)
        table.update(table_input)
        return ""

    def get_table_versions(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        table = self.glue_backend.get_table(database_name, table_name)

        return json.dumps(
            {
                "TableVersions": [
                    {"Table": table.as_dict(version=n), "VersionId": str(n + 1)}
                    for n in range(len(table.versions))
                ]
            }
        )

    def get_table_version(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        table = self.glue_backend.get_table(database_name, table_name)
        ver_id = self.parameters.get("VersionId")

        return json.dumps(
            {
                "TableVersion": {
                    "Table": table.as_dict(version=ver_id),
                    "VersionId": ver_id,
                }
            }
        )

    def get_tables(self):
        database_name = self.parameters.get("DatabaseName")
        tables = self.glue_backend.get_tables(database_name)
        return json.dumps({"TableList": [table.as_dict() for table in tables]})

    def delete_table(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("Name")
        resp = self.glue_backend.delete_table(database_name, table_name)
        return json.dumps(resp)

    def batch_delete_table(self):
        database_name = self.parameters.get("DatabaseName")

        errors = []
        for table_name in self.parameters.get("TablesToDelete"):
            try:
                self.glue_backend.delete_table(database_name, table_name)
            except TableNotFoundException:
                errors.append(
                    {
                        "TableName": table_name,
                        "ErrorDetail": {
                            "ErrorCode": "EntityNotFoundException",
                            "ErrorMessage": "Table not found",
                        },
                    }
                )

        out = {}
        if errors:
            out["Errors"] = errors

        return json.dumps(out)

    def get_partitions(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        expression = self.parameters.get("Expression")
        partitions = self.glue_backend.get_partitions(
            database_name, table_name, expression
        )

        return json.dumps({"Partitions": [p.as_dict() for p in partitions]})

    def get_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        values = self.parameters.get("PartitionValues")

        table = self.glue_backend.get_table(database_name, table_name)

        p = table.get_partition(values)

        return json.dumps({"Partition": p.as_dict()})

    def batch_get_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        partitions_to_get = self.parameters.get("PartitionsToGet")

        table = self.glue_backend.get_table(database_name, table_name)

        partitions = []
        for values in partitions_to_get:
            try:
                p = table.get_partition(values=values["Values"])
                partitions.append(p.as_dict())
            except PartitionNotFoundException:
                continue

        return json.dumps({"Partitions": partitions})

    def create_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        part_input = self.parameters.get("PartitionInput")

        table = self.glue_backend.get_table(database_name, table_name)
        table.create_partition(part_input)

        return ""

    def batch_create_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        table = self.glue_backend.get_table(database_name, table_name)

        errors_output = []
        for part_input in self.parameters.get("PartitionInputList"):
            try:
                table.create_partition(part_input)
            except PartitionAlreadyExistsException:
                errors_output.append(
                    {
                        "PartitionValues": part_input["Values"],
                        "ErrorDetail": {
                            "ErrorCode": "AlreadyExistsException",
                            "ErrorMessage": "Partition already exists.",
                        },
                    }
                )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return json.dumps(out)

    def update_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        part_input = self.parameters.get("PartitionInput")
        part_to_update = self.parameters.get("PartitionValueList")

        table = self.glue_backend.get_table(database_name, table_name)
        table.update_partition(part_to_update, part_input)

        return ""

    def batch_update_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        table = self.glue_backend.get_table(database_name, table_name)

        errors_output = []
        for entry in self.parameters.get("Entries"):
            part_to_update = entry["PartitionValueList"]
            part_input = entry["PartitionInput"]

            try:
                table.update_partition(part_to_update, part_input)
            except PartitionNotFoundException:
                errors_output.append(
                    {
                        "PartitionValueList": part_to_update,
                        "ErrorDetail": {
                            "ErrorCode": "EntityNotFoundException",
                            "ErrorMessage": "Partition not found.",
                        },
                    }
                )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return json.dumps(out)

    def delete_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        part_to_delete = self.parameters.get("PartitionValues")

        table = self.glue_backend.get_table(database_name, table_name)
        table.delete_partition(part_to_delete)

        return ""

    def batch_delete_partition(self):
        database_name = self.parameters.get("DatabaseName")
        table_name = self.parameters.get("TableName")
        table = self.glue_backend.get_table(database_name, table_name)

        errors_output = []
        for part_input in self.parameters.get("PartitionsToDelete"):
            values = part_input.get("Values")
            try:
                table.delete_partition(values)
            except PartitionNotFoundException:
                errors_output.append(
                    {
                        "PartitionValues": values,
                        "ErrorDetail": {
                            "ErrorCode": "EntityNotFoundException",
                            "ErrorMessage": "Partition not found",
                        },
                    }
                )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return json.dumps(out)

    def create_crawler(self):
        self.glue_backend.create_crawler(
            name=self.parameters.get("Name"),
            role=self.parameters.get("Role"),
            database_name=self.parameters.get("DatabaseName"),
            description=self.parameters.get("Description"),
            targets=self.parameters.get("Targets"),
            schedule=self.parameters.get("Schedule"),
            classifiers=self.parameters.get("Classifiers"),
            table_prefix=self.parameters.get("TablePrefix"),
            schema_change_policy=self.parameters.get("SchemaChangePolicy"),
            recrawl_policy=self.parameters.get("RecrawlPolicy"),
            lineage_configuration=self.parameters.get("LineageConfiguration"),
            configuration=self.parameters.get("Configuration"),
            crawler_security_configuration=self.parameters.get(
                "CrawlerSecurityConfiguration"
            ),
            tags=self.parameters.get("Tags"),
        )
        return ""

    def get_crawler(self):
        name = self.parameters.get("Name")
        crawler = self.glue_backend.get_crawler(name)
        return json.dumps({"Crawler": crawler.as_dict()})

    def get_crawlers(self):
        crawlers = self.glue_backend.get_crawlers()
        return json.dumps({"Crawlers": [crawler.as_dict() for crawler in crawlers]})

    def list_crawlers(self):
        next_token = self._get_param("NextToken")
        max_results = self._get_int_param("MaxResults")
        tags = self._get_param("Tags")
        crawlers, next_token = self.glue_backend.list_crawlers(
            next_token=next_token, max_results=max_results
        )
        filtered_crawler_names = self.filter_crawlers_by_tags(crawlers, tags)
        return json.dumps(
            dict(
                CrawlerNames=[crawler_name for crawler_name in filtered_crawler_names],
                NextToken=next_token,
            )
        )

    def filter_crawlers_by_tags(self, crawlers, tags):
        if not tags:
            return [crawler.get_name() for crawler in crawlers]
        return [
            crawler.get_name()
            for crawler in crawlers
            if self.is_tags_match(self, crawler.arn, tags)
        ]

    def start_crawler(self):
        name = self.parameters.get("Name")
        self.glue_backend.start_crawler(name)
        return ""

    def stop_crawler(self):
        name = self.parameters.get("Name")
        self.glue_backend.stop_crawler(name)
        return ""

    def delete_crawler(self):
        name = self.parameters.get("Name")
        self.glue_backend.delete_crawler(name)
        return ""

    def create_job(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        log_uri = self._get_param("LogUri")
        role = self._get_param("Role")
        execution_property = self._get_param("ExecutionProperty")
        command = self._get_param("Command")
        default_arguments = self._get_param("DefaultArguments")
        non_overridable_arguments = self._get_param("NonOverridableArguments")
        connections = self._get_param("Connections")
        max_retries = self._get_int_param("MaxRetries")
        allocated_capacity = self._get_int_param("AllocatedCapacity")
        timeout = self._get_int_param("Timeout")
        max_capacity = self._get_param("MaxCapacity")
        security_configuration = self._get_param("SecurityConfiguration")
        tags = self._get_param("Tags")
        notification_property = self._get_param("NotificationProperty")
        glue_version = self._get_param("GlueVersion")
        number_of_workers = self._get_int_param("NumberOfWorkers")
        worker_type = self._get_param("WorkerType")
        name = self.glue_backend.create_job(
            name=name,
            description=description,
            log_uri=log_uri,
            role=role,
            execution_property=execution_property,
            command=command,
            default_arguments=default_arguments,
            non_overridable_arguments=non_overridable_arguments,
            connections=connections,
            max_retries=max_retries,
            allocated_capacity=allocated_capacity,
            timeout=timeout,
            max_capacity=max_capacity,
            security_configuration=security_configuration,
            tags=tags,
            notification_property=notification_property,
            glue_version=glue_version,
            number_of_workers=number_of_workers,
            worker_type=worker_type,
        )
        return json.dumps(dict(Name=name))

    def get_job(self):
        name = self.parameters.get("JobName")
        job = self.glue_backend.get_job(name)
        return json.dumps({"Job": job.as_dict()})

    def start_job_run(self):
        name = self.parameters.get("JobName")
        job_run_id = self.glue_backend.start_job_run(name)
        return json.dumps(dict(JobRunId=job_run_id))

    def get_job_run(self):
        name = self.parameters.get("JobName")
        run_id = self.parameters.get("RunId")
        job_run = self.glue_backend.get_job_run(name, run_id)
        return json.dumps({"JobRun": job_run.as_dict()})

    def list_jobs(self):
        next_token = self._get_param("NextToken")
        max_results = self._get_int_param("MaxResults")
        tags = self._get_param("Tags")
        jobs, next_token = self.glue_backend.list_jobs(
            next_token=next_token, max_results=max_results
        )
        filtered_job_names = self.filter_jobs_by_tags(jobs, tags)
        return json.dumps(
            dict(
                JobNames=[job_name for job_name in filtered_job_names],
                NextToken=next_token,
            )
        )

    def get_tags(self):
        resource_arn = self.parameters.get("ResourceArn")
        tags = self.glue_backend.get_tags(resource_arn)
        return 200, {}, json.dumps({"Tags": tags})

    def tag_resource(self):
        resource_arn = self.parameters.get("ResourceArn")
        tags = self.parameters.get("TagsToAdd", {})
        self.glue_backend.tag_resource(resource_arn, tags)
        return 201, {}, "{}"

    def untag_resource(self):
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self.parameters.get("TagsToRemove")
        self.glue_backend.untag_resource(resource_arn, tag_keys)
        return 200, {}, "{}"

    def filter_jobs_by_tags(self, jobs, tags):
        if not tags:
            return [job.get_name() for job in jobs]
        return [
            job.get_name() for job in jobs if self.is_tags_match(self, job.arn, tags)
        ]

    @staticmethod
    def is_tags_match(self, resource_arn, tags):
        glue_resource_tags = self.glue_backend.get_tags(resource_arn)
        mutual_keys = set(glue_resource_tags).intersection(tags)
        for key in mutual_keys:
            if glue_resource_tags[key] == tags[key]:
                return True
        return False

    def create_registry(self):
        registry_name = self._get_param("RegistryName")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        registry = self.glue_backend.create_registry(registry_name, description, tags)
        return json.dumps(registry)

    def create_schema(self):
        registry_id = self._get_param("RegistryId")
        schema_name = self._get_param("SchemaName")
        data_format = self._get_param("DataFormat")
        compatibility = self._get_param("Compatibility")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        schema_definition = self._get_param("SchemaDefinition")
        schema = self.glue_backend.create_schema(
            registry_id,
            schema_name,
            data_format,
            compatibility,
            schema_definition,
            description,
            tags,
        )
        return json.dumps(schema)

    def register_schema_version(self):
        schema_id = self._get_param("SchemaId")
        schema_definition = self._get_param("SchemaDefinition")
        schema_version = self.glue_backend.register_schema_version(
            schema_id, schema_definition
        )
        return json.dumps(schema_version)

    def get_schema_version(self):
        schema_id = self._get_param("SchemaId")
        schema_version_id = self._get_param("SchemaVersionId")
        schema_version_number = self._get_param("SchemaVersionNumber")

        schema_version = self.glue_backend.get_schema_version(
            schema_id, schema_version_id, schema_version_number
        )
        return json.dumps(schema_version)

    def get_schema_by_definition(self):
        schema_id = self._get_param("SchemaId")
        schema_definition = self._get_param("SchemaDefinition")
        schema_version = self.glue_backend.get_schema_by_definition(
            schema_id, schema_definition
        )
        return json.dumps(schema_version)

    def put_schema_version_metadata(self):
        schema_id = self._get_param("SchemaId")
        schema_version_number = self._get_param("SchemaVersionNumber")
        schema_version_id = self._get_param("SchemaVersionId")
        metadata_key_value = self._get_param("MetadataKeyValue")
        schema_version = self.glue_backend.put_schema_version_metadata(
            schema_id, schema_version_number, schema_version_id, metadata_key_value
        )
        return json.dumps(schema_version)

    def delete_schema(self):
        schema_id = self._get_param("SchemaId")
        schema = self.glue_backend.delete_schema(schema_id)
        return json.dumps(schema)
