from moto.core.responses import (
    ActionResult,
    BaseResponse,
    EmptyResult,
    PaginatedResult,
)

from .exceptions import EntityNotFoundException, InvalidInputException
from .models import (
    FakeCrawler,
    FakeJob,
    FakeSession,
    FakeTrigger,
    GlueBackend,
    glue_backends,
)
from .utils import Action, Predicate, validate_crawl_filters


class GlueResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="glue")
        self.automated_parameter_parsing = True

    @property
    def glue_backend(self) -> GlueBackend:
        return glue_backends[self.current_account][self.region]

    def create_database(self) -> ActionResult:
        database_input = self._get_param("DatabaseInput")
        database_name = database_input.get("Name")
        if "CatalogId" in self.params:
            database_input["CatalogId"] = self._get_param("CatalogId")
        self.glue_backend.create_database(
            database_name,
            database_input,
            self._get_param("Tags"),
        )
        return EmptyResult()

    def get_database(self) -> ActionResult:
        database_name = self._get_param("Name")
        database = self.glue_backend.get_database(database_name)
        return ActionResult({"Database": database.as_dict()})

    def get_databases(self) -> ActionResult:
        database_list = self.glue_backend.get_databases()
        return ActionResult(
            {"DatabaseList": [database.as_dict() for database in database_list]}
        )

    def update_database(self) -> ActionResult:
        database_input = self._get_param("DatabaseInput")
        database_name = self._get_param("Name")
        if "CatalogId" in self.params:
            database_input["CatalogId"] = self._get_param("CatalogId")
        self.glue_backend.update_database(database_name, database_input)
        return EmptyResult()

    def delete_database(self) -> EmptyResult:
        name = self._get_param("Name")
        self.glue_backend.delete_database(name)
        return EmptyResult()

    def create_table(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_input = self._get_param("TableInput")
        table_name = table_input.get("Name")
        open_table_format_input = self._get_param("OpenTableFormatInput")
        self.glue_backend.create_table(
            database_name,
            table_name,
            table_input,
            open_table_format_input,
        )
        return EmptyResult()

    def get_table(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("Name")
        table = self.glue_backend.get_table(database_name, table_name)

        return ActionResult({"Table": table.as_dict()})

    def update_table(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_input = self._get_param("TableInput")
        table_name = table_input.get("Name")
        self.glue_backend.update_table(database_name, table_name, table_input)
        return EmptyResult()

    def get_table_versions(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        versions = self.glue_backend.get_table_versions(database_name, table_name)
        return ActionResult(
            {
                "TableVersions": [
                    {"Table": data, "VersionId": version}
                    for version, data in versions.items()
                ]
            }
        )

    def get_table_version(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        ver_id = self._get_param("VersionId")
        return ActionResult(
            self.glue_backend.get_table_version(database_name, table_name, ver_id)
        )

    def delete_table_version(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        version_id = self._get_param("VersionId")
        self.glue_backend.delete_table_version(database_name, table_name, version_id)
        return EmptyResult()

    def get_tables(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        expression = self._get_param("Expression")
        tables = self.glue_backend.get_tables(database_name, expression)
        return ActionResult({"TableList": [table.as_dict() for table in tables]})

    def delete_table(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("Name")
        self.glue_backend.delete_table(database_name, table_name)
        return EmptyResult()

    def batch_delete_table(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")

        tables = self._get_param("TablesToDelete")
        errors = self.glue_backend.batch_delete_table(database_name, tables)

        out = {}
        if errors:
            out["Errors"] = errors

        return ActionResult(out)

    def get_partitions(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        expression = self._get_param("Expression")
        segment = self._get_param("Segment")
        exclude_column_schema = self._get_bool_param("ExcludeColumnSchema", False)
        partitions = self.glue_backend.get_partitions(
            database_name,
            table_name,
            expression,
            segment=segment,
        )

        return PaginatedResult(
            {
                "Partitions": [
                    p.as_dict(exclude_column_schema=exclude_column_schema)
                    for p in partitions
                ]
            }
        )

    def get_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        values = self._get_param("PartitionValues")

        p = self.glue_backend.get_partition(database_name, table_name, values)

        return ActionResult({"Partition": p.as_dict()})

    def batch_get_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        partitions_to_get = self._get_param("PartitionsToGet")

        partitions = self.glue_backend.batch_get_partition(
            database_name,
            table_name,
            partitions_to_get,
        )

        return ActionResult({"Partitions": partitions})

    def create_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        part_input = self._get_param("PartitionInput")

        self.glue_backend.create_partition(database_name, table_name, part_input)
        return EmptyResult()

    def batch_create_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        partition_input = self._get_param("PartitionInputList")
        errors_output = self.glue_backend.batch_create_partition(
            database_name,
            table_name,
            partition_input,
        )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return ActionResult(out)

    def update_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        part_input = self._get_param("PartitionInput")
        part_to_update = self._get_param("PartitionValueList")

        self.glue_backend.update_partition(
            database_name,
            table_name,
            part_input,
            part_to_update,
        )
        return EmptyResult()

    def batch_update_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        entries = self._get_param("Entries")

        errors_output = self.glue_backend.batch_update_partition(
            database_name,
            table_name,
            entries,
        )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return ActionResult(out)

    def delete_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        part_to_delete = self._get_param("PartitionValues")

        self.glue_backend.delete_partition(database_name, table_name, part_to_delete)
        return EmptyResult()

    def batch_delete_partition(self) -> ActionResult:
        database_name = self._get_param("DatabaseName")
        table_name = self._get_param("TableName")
        parts = self._get_param("PartitionsToDelete")

        errors_output = self.glue_backend.batch_delete_partition(
            database_name,
            table_name,
            parts,
        )

        out = {}
        if errors_output:
            out["Errors"] = errors_output

        return ActionResult(out)

    def create_crawler(self) -> ActionResult:
        self.glue_backend.create_crawler(
            name=self._get_param("Name"),
            role=self._get_param("Role"),
            database_name=self._get_param("DatabaseName"),
            description=self._get_param("Description"),
            targets=self._get_param("Targets"),
            schedule=self._get_param("Schedule"),
            classifiers=self._get_param("Classifiers"),
            table_prefix=self._get_param("TablePrefix"),
            schema_change_policy=self._get_param("SchemaChangePolicy"),
            recrawl_policy=self._get_param("RecrawlPolicy"),
            lineage_configuration=self._get_param("LineageConfiguration"),
            configuration=self._get_param("Configuration"),
            crawler_security_configuration=self._get_param(
                "CrawlerSecurityConfiguration"
            ),
            tags=self._get_param("Tags"),
        )
        return EmptyResult()

    def get_crawler(self) -> ActionResult:
        name = self._get_param("Name")
        crawler = self.glue_backend.get_crawler(name)
        return ActionResult({"Crawler": crawler.as_dict()})

    def get_crawlers(self) -> ActionResult:
        crawlers = self.glue_backend.get_crawlers()
        return ActionResult({"Crawlers": [crawler.as_dict() for crawler in crawlers]})

    def list_crawlers(self) -> ActionResult:
        tags = self._get_param("Tags")
        crawlers = self.glue_backend.list_crawlers()
        filtered_crawler_names = self.filter_crawlers_by_tags(crawlers, tags)
        return PaginatedResult({"CrawlerNames": filtered_crawler_names})

    def filter_crawlers_by_tags(
        self, crawlers: list[FakeCrawler], tags: dict[str, str]
    ) -> list[str]:
        if not tags:
            return [crawler.get_name() for crawler in crawlers]
        return [
            crawler.get_name()
            for crawler in crawlers
            if self.is_tags_match(crawler.arn, tags)
        ]

    def start_crawler(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.start_crawler(name)
        return EmptyResult()

    def stop_crawler(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.stop_crawler(name)
        return EmptyResult()

    def delete_crawler(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.delete_crawler(name)
        return EmptyResult()

    def list_crawls(self) -> ActionResult:
        crawler_name = self._get_param("CrawlerName")
        filters = validate_crawl_filters(self._get_param("Filters", []))
        crawls = self.glue_backend.list_crawls(crawler_name, filters)
        return PaginatedResult({"Crawls": [crawl.as_dict() for crawl in crawls]})

    def create_job(self) -> ActionResult:
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
        code_gen_configuration_nodes = self._get_param("CodeGenConfigurationNodes")
        execution_class = self._get_param("ExecutionClass")
        source_control_details = self._get_param("SourceControlDetails")
        self.glue_backend.create_job(
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
            code_gen_configuration_nodes=code_gen_configuration_nodes,
            execution_class=execution_class,
            source_control_details=source_control_details,
        )
        return ActionResult({"Name": name})

    def get_job(self) -> ActionResult:
        name = self._get_param("JobName")
        job = self.glue_backend.get_job(name)
        return ActionResult({"Job": job.as_dict()})

    def get_jobs(self) -> ActionResult:
        jobs = self.glue_backend.get_jobs()
        return PaginatedResult({"Jobs": [job.as_dict() for job in jobs]})

    def start_job_run(self) -> ActionResult:
        allocated_capacity = self._get_int_param("AllocatedCapacity")
        notification_property = self._get_param("NotificationProperty")
        number_of_workers = self._get_int_param("NumberOfWorkers")
        security_configuration = self._get_param("SecurityConfiguration")
        timeout = self._get_int_param("Timeout")
        worker_type = self._get_param("WorkerType")
        name = self._get_param("JobName")
        arguments = self._get_param("Arguments")
        max_capacity = self._get_float_param("MaxCapacity")
        previous_job_run_id = self._get_param("JobRunId")

        if allocated_capacity and max_capacity:
            raise InvalidInputException(
                "StartJobRun", "Please set only Allocated Capacity or Max Capacity"
            )

        job_run_id = self.glue_backend.start_job_run(
            name,
            arguments,
            allocated_capacity,
            max_capacity,
            timeout,
            worker_type,
            security_configuration,
            number_of_workers,
            notification_property,
            previous_job_run_id,
        )
        return ActionResult({"JobRunId": job_run_id})

    def get_job_run(self) -> ActionResult:
        name = self._get_param("JobName")
        run_id = self._get_param("RunId")
        job_run = self.glue_backend.get_job_run(name, run_id)
        return ActionResult({"JobRun": job_run.as_dict()})

    def get_job_runs(self) -> ActionResult:
        job_name = self._get_param("JobName")
        job_runs = self.glue_backend.get_job_runs(job_name)
        return PaginatedResult({"JobRuns": [job_run.as_dict() for job_run in job_runs]})

    def list_jobs(self) -> ActionResult:
        tags = self._get_param("Tags")
        jobs = self.glue_backend.list_jobs()
        filtered_job_names = self.filter_jobs_by_tags(jobs, tags)
        return PaginatedResult({"JobNames": filtered_job_names})

    def delete_job(self) -> ActionResult:
        name = self._get_param("JobName")
        self.glue_backend.delete_job(name)
        return ActionResult({"JobName": name})

    def get_tags(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self.glue_backend.get_tags(resource_arn)
        return ActionResult({"Tags": tags})

    def tag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tags = self._get_param("TagsToAdd", {})
        self.glue_backend.tag_resource(resource_arn, tags)
        return EmptyResult()

    def untag_resource(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        tag_keys = self._get_param("TagsToRemove")
        self.glue_backend.untag_resource(resource_arn, tag_keys)
        return EmptyResult()

    def filter_jobs_by_tags(
        self, jobs: list[FakeJob], tags: dict[str, str]
    ) -> list[str]:
        if not tags:
            return [job.get_name() for job in jobs]
        return [job.get_name() for job in jobs if self.is_tags_match(job.arn, tags)]

    def filter_triggers_by_tags(
        self, triggers: list[FakeTrigger], tags: dict[str, str]
    ) -> list[str]:
        if not tags:
            return [trigger.get_name() for trigger in triggers]
        return [
            trigger.get_name()
            for trigger in triggers
            if self.is_tags_match(trigger.arn, tags)
        ]

    def is_tags_match(self, resource_arn: str, tags: dict[str, str]) -> bool:
        glue_resource_tags = self.glue_backend.get_tags(resource_arn)
        mutual_keys = set(glue_resource_tags).intersection(tags)
        for key in mutual_keys:
            if glue_resource_tags[key] == tags[key]:
                return True
        return False

    def create_registry(self) -> ActionResult:
        registry_name = self._get_param("RegistryName")
        description = self._get_param("Description")
        tags = self._get_param("Tags")
        registry = self.glue_backend.create_registry(registry_name, description, tags)
        return ActionResult(registry)

    def delete_registry(self) -> ActionResult:
        registry_id = self._get_param("RegistryId")
        registry = self.glue_backend.delete_registry(registry_id)
        return ActionResult(registry)

    def get_registry(self) -> ActionResult:
        registry_id = self._get_param("RegistryId")
        registry = self.glue_backend.get_registry(registry_id)
        return ActionResult(registry)

    def list_registries(self) -> ActionResult:
        registries = self.glue_backend.list_registries()
        return ActionResult({"Registries": registries})

    def create_schema(self) -> ActionResult:
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
        return ActionResult(schema)

    def register_schema_version(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema_definition = self._get_param("SchemaDefinition")
        schema_version = self.glue_backend.register_schema_version(
            schema_id, schema_definition
        )
        return ActionResult(schema_version)

    def get_schema_version(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema_version_id = self._get_param("SchemaVersionId")
        schema_version_number = self._get_param("SchemaVersionNumber")

        schema_version = self.glue_backend.get_schema_version(
            schema_id, schema_version_id, schema_version_number
        )
        return ActionResult(schema_version)

    def get_schema_by_definition(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema_definition = self._get_param("SchemaDefinition")
        schema_version = self.glue_backend.get_schema_by_definition(
            schema_id, schema_definition
        )
        return ActionResult(schema_version)

    def put_schema_version_metadata(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema_version_number = self._get_param("SchemaVersionNumber")
        schema_version_id = self._get_param("SchemaVersionId")
        metadata_key_value = self._get_param("MetadataKeyValue")
        schema_version = self.glue_backend.put_schema_version_metadata(
            schema_id, schema_version_number, schema_version_id, metadata_key_value
        )
        return ActionResult(schema_version)

    def get_schema(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema = self.glue_backend.get_schema(schema_id)
        return ActionResult(schema)

    def delete_schema(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        schema = self.glue_backend.delete_schema(schema_id)
        return ActionResult(schema)

    def update_schema(self) -> ActionResult:
        schema_id = self._get_param("SchemaId")
        compatibility = self._get_param("Compatibility")
        description = self._get_param("Description")
        schema = self.glue_backend.update_schema(schema_id, compatibility, description)
        return ActionResult(schema)

    def create_session(self) -> ActionResult:
        self.glue_backend.create_session(
            session_id=self._get_param("Id"),
            description=self._get_param("Description"),
            role=self._get_param("Role"),
            command=self._get_param("Command"),
            timeout=self._get_param("Timeout"),
            idle_timeout=self._get_param("IdleTimeout"),
            default_arguments=self._get_param("DefaultArguments"),
            connections=self._get_param("Connections"),
            max_capacity=self._get_param("MaxCapacity"),
            number_of_workers=self._get_param("NumberOfWorkers"),
            worker_type=self._get_param("WorkerType"),
            security_configuration=self._get_param("SecurityConfiguration"),
            glue_version=self._get_param("GlueVersion"),
            tags=self._get_param("Tags"),
            request_origin=self._get_param("RequestOrigin"),
        )
        return EmptyResult()

    def get_session(self) -> ActionResult:
        session_id = self._get_param("Id")
        session = self.glue_backend.get_session(session_id)
        return ActionResult({"Session": session.as_dict()})

    def list_sessions(self) -> ActionResult:
        tags = self._get_param("Tags")
        sessions = self.glue_backend.list_sessions()
        filtered_session_ids = self._filter_sessions_by_tags(sessions, tags)
        return PaginatedResult(
            {
                "Ids": filtered_session_ids,
                "Sessions": [
                    self.glue_backend.get_session(session_id).as_dict()
                    for session_id in filtered_session_ids
                ],
            }
        )

    def _filter_sessions_by_tags(
        self, sessions: list[FakeSession], tags: dict[str, str]
    ) -> list[str]:
        if not tags:
            return [session.get_id() for session in sessions]
        return [
            session.get_id()
            for session in sessions
            if self.is_tags_match(session.arn, tags)
        ]

    def stop_session(self) -> ActionResult:
        session_id = self._get_param("Id")
        self.glue_backend.stop_session(session_id)
        return ActionResult({"Id": session_id})

    def delete_session(self) -> ActionResult:
        session_id = self._get_param("Id")
        self.glue_backend.delete_session(session_id)
        return ActionResult({"Id": session_id})

    def batch_get_crawlers(self) -> ActionResult:
        crawler_names = self._get_param("CrawlerNames")
        crawlers = self.glue_backend.batch_get_crawlers(crawler_names)
        crawlers_not_found = list(
            set(crawler_names) - {crawler["Name"] for crawler in crawlers}
        )
        return ActionResult(
            {
                "Crawlers": crawlers,
                "CrawlersNotFound": crawlers_not_found,
            }
        )

    def batch_get_jobs(self) -> ActionResult:
        job_names = self._get_param("JobNames")
        jobs = self.glue_backend.batch_get_jobs(job_names)
        jobs_not_found = list(set(job_names) - {job["Name"] for job in jobs})
        return ActionResult(
            {
                "Jobs": jobs,
                "JobsNotFound": jobs_not_found,
            }
        )

    def get_partition_indexes(self) -> ActionResult:
        return ActionResult({"PartitionIndexDescriptorList": []})

    def create_trigger(self) -> ActionResult:
        name = self._get_param("Name")
        workflow_name = self._get_param("WorkflowName")
        trigger_type = self._get_param("Type")
        schedule = self._get_param("Schedule")

        predicate_input: dict[str, str | list[dict[str, str]]] | None = self._get_param(
            "Predicate"
        )
        if predicate_input:
            predicate = Predicate(predicate_input)
        else:
            predicate = None

        actions = [Action(inputs) for inputs in self._get_param("Actions", [])]
        description = self._get_param("Description")
        start_on_creation = self._get_param("StartOnCreation")
        tags = self._get_param("Tags")
        event_batching_condition = self._get_param("EventBatchingCondition")

        if trigger_type == "CONDITIONAL" and not predicate:
            raise InvalidInputException(
                "CreateTrigger", "Predicate cannot be null or empty"
            )

        self.glue_backend.create_trigger(
            name=name,
            workflow_name=workflow_name,
            trigger_type=trigger_type,
            schedule=schedule,
            predicate=predicate,
            actions=actions,
            description=description,
            start_on_creation=start_on_creation,
            tags=tags,
            event_batching_condition=event_batching_condition,
        )
        return ActionResult({"Name": name})

    def get_trigger(self) -> ActionResult:
        name = self._get_param("Name")
        trigger = self.glue_backend.get_trigger(name)
        return ActionResult({"Trigger": trigger.as_dict()})

    def get_triggers(self) -> ActionResult:
        dependent_job_name = self._get_param("DependentJobName")
        triggers = self.glue_backend.get_triggers(dependent_job_name=dependent_job_name)
        return PaginatedResult(
            {"Triggers": [trigger.as_dict() for trigger in triggers]}
        )

    def list_triggers(self) -> ActionResult:
        dependent_job_name = self._get_param("DependentJobName")
        tags = self._get_param("Tags")
        triggers = self.glue_backend.list_triggers(
            dependent_job_name=dependent_job_name
        )
        filtered_trigger_names = self.filter_triggers_by_tags(triggers, tags)
        return PaginatedResult({"TriggerNames": filtered_trigger_names})

    def batch_get_triggers(self) -> ActionResult:
        trigger_names = self._get_param("TriggerNames")
        triggers = self.glue_backend.batch_get_triggers(trigger_names)
        triggers_not_found = list(
            set(trigger_names) - {trigger["Name"] for trigger in triggers}
        )
        return ActionResult(
            {
                "Triggers": triggers,
                "TriggersNotFound": triggers_not_found,
            }
        )

    def start_trigger(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.start_trigger(name)
        return ActionResult({"Name": name})

    def stop_trigger(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.stop_trigger(name)
        return ActionResult({"Name": name})

    def delete_trigger(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.delete_trigger(name)
        return ActionResult({"Name": name})

    def get_dev_endpoints(self) -> ActionResult:
        endpoints = self.glue_backend.get_dev_endpoints()
        return PaginatedResult(
            {"DevEndpoints": [endpoint.as_dict() for endpoint in endpoints]}
        )

    def create_dev_endpoint(self) -> ActionResult:
        endpoint_name = self._get_param("EndpointName")
        role_arn = self._get_param("RoleArn")
        security_group_ids = self._get_param("SecurityGroupIds")
        subnet_id = self._get_param("SubnetId")
        public_key = self._get_param("PublicKey")
        public_keys = self._get_param("PublicKeys")
        number_of_nodes = self._get_int_param("NumberOfNodes")
        worker_type = self._get_param("WorkerType", "Standard")
        glue_version = self._get_param("GlueVersion", "1.0")
        number_of_workers = self._get_int_param("NumberOfWorkers")
        extra_python_libs_s3_path = self._get_param("ExtraPythonLibsS3Path")
        extra_jars_s3_path = self._get_param("ExtraJarsS3Path")
        security_configuration = self._get_param("SecurityConfiguration")
        tags = self._get_param("Tags")
        arguments = self._get_param("Arguments")

        dev_endpoint = self.glue_backend.create_dev_endpoint(
            endpoint_name=endpoint_name,
            role_arn=role_arn,
            security_group_ids=security_group_ids,
            subnet_id=subnet_id,
            public_key=public_key,
            public_keys=public_keys,
            number_of_nodes=number_of_nodes,
            worker_type=worker_type,
            glue_version=glue_version,
            number_of_workers=number_of_workers,
            extra_python_libs_s3_path=extra_python_libs_s3_path,
            extra_jars_s3_path=extra_jars_s3_path,
            security_configuration=security_configuration,
            tags=tags,
            arguments=arguments,
        )

        return ActionResult(dev_endpoint.as_dict())

    def get_dev_endpoint(self) -> ActionResult:
        endpoint_name = self._get_param("EndpointName")
        dev_endpoint = self.glue_backend.get_dev_endpoint(endpoint_name)
        return ActionResult({"DevEndpoint": dev_endpoint.as_dict()})

    def delete_dev_endpoint(self) -> ActionResult:
        endpoint_name = self._get_param("EndpointName")
        self.glue_backend.delete_dev_endpoint(endpoint_name)
        return EmptyResult()

    def create_ml_transform(self) -> ActionResult:
        name = self._get_param("Name")
        input_record_tables = self._get_param("InputRecordTables")
        parameters = self._get_param("Parameters")
        role = self._get_param("Role")
        description = self._get_param("Description")
        glue_version = self._get_param("GlueVersion")
        max_capacity = self._get_param("MaxCapacity")
        worker_type = self._get_param("WorkerType")
        number_of_workers = self._get_int_param("NumberOfWorkers")
        timeout = self._get_int_param("Timeout")
        max_retries = self._get_int_param("MaxRetries")
        tags = self._get_param("Tags")
        transform_encryption = self._get_param("TransformEncryption")

        transform_id = self.glue_backend.create_ml_transform(
            name=name,
            input_record_tables=input_record_tables,
            parameters=parameters,
            role=role,
            description=description,
            glue_version=glue_version,
            max_capacity=max_capacity,
            worker_type=worker_type,
            number_of_workers=number_of_workers,
            timeout=timeout,
            max_retries=max_retries,
            tags=tags,
            transform_encryption=transform_encryption,
        )
        return ActionResult({"TransformId": transform_id})

    def get_ml_transform(self) -> ActionResult:
        transform_id = self._get_param("TransformId")
        ml_transform = self.glue_backend.get_ml_transform(transform_id)
        return ActionResult(ml_transform.as_dict())

    def get_ml_transforms(self) -> ActionResult:
        ml_transforms = self.glue_backend.get_ml_transforms()
        return PaginatedResult(
            {"Transforms": [transform.as_dict() for transform in ml_transforms]}
        )

    def delete_ml_transform(self) -> ActionResult:
        transform_id = self._get_param("TransformId")
        transform_id = self.glue_backend.delete_ml_transform(transform_id)
        return ActionResult({"TransformId": transform_id})

    def create_connection(self) -> ActionResult:
        catalog_id = self._get_param("CatalogId")
        connection_input = self._get_param("ConnectionInput")
        tags = self._get_param("Tags")
        create_connection_status = self.glue_backend.create_connection(
            catalog_id=catalog_id,
            connection_input=connection_input,
            tags=tags,
        )
        return ActionResult({"CreateConnectionStatus": create_connection_status})

    def get_connection(self) -> ActionResult:
        catalog_id = self._get_param("CatalogId")
        name = self._get_param("Name")
        hide_password = self._get_param("HidePassword")
        apply_override_for_compute_environment = self._get_param(
            "ApplyOverrideForComputeEnvironment"
        )
        connection = self.glue_backend.get_connection(
            catalog_id=catalog_id,
            name=name,
            apply_override_for_compute_environment=apply_override_for_compute_environment,
        )
        return ActionResult({"Connection": connection.as_dict(hide_password)})

    def get_connections(self) -> ActionResult:
        catalog_id = self._get_param("CatalogId")
        filter = self._get_param("Filter")
        hide_password = self._get_param("HidePassword")
        connections = self.glue_backend.get_connections(
            catalog_id=catalog_id, filter=filter
        )
        connection_list = [
            connection.as_dict(hide_password) for connection in connections
        ]
        return PaginatedResult({"ConnectionList": connection_list})

    def put_data_catalog_encryption_settings(self) -> ActionResult:
        catalog_id = self._get_param("CatalogId", None)
        data_catalog_encryption_settings = self._get_param(
            "DataCatalogEncryptionSettings", {}
        )

        self.glue_backend.put_data_catalog_encryption_settings(
            catalog_id=catalog_id,
            data_catalog_encryption_settings=data_catalog_encryption_settings,
        )

        return EmptyResult()

    def get_data_catalog_encryption_settings(self) -> ActionResult:
        catalog_id = self._get_param("CatalogId", None)

        response = self.glue_backend.get_data_catalog_encryption_settings(
            catalog_id=catalog_id,
        )

        return ActionResult(response)

    def put_resource_policy(self) -> ActionResult:
        policy_in_json = self._get_param("PolicyInJson")
        resource_arn = self._get_param("ResourceArn")
        policy_hash_condition = self._get_param("PolicyHashCondition")
        policy_exists_condition = self._get_param("PolicyExistsCondition")
        enable_hybrid = self._get_param("EnableHybrid")

        policy_hash = self.glue_backend.put_resource_policy(
            policy_in_json=policy_in_json,
            resource_arn=resource_arn,
            policy_hash_condition=policy_hash_condition,
            policy_exists_condition=policy_exists_condition,
            enable_hybrid=enable_hybrid,
        )

        return ActionResult(policy_hash)

    def get_resource_policy(self) -> ActionResult:
        resource_arn = self._get_param("ResourceArn")
        response = self.glue_backend.get_resource_policy(
            resource_arn=resource_arn,
        )

        return ActionResult(response)

    def delete_resource_policy(self) -> ActionResult:
        policy_hash_condition = self._get_param("PolicyHashCondition")
        resource_arn = self._get_param("ResourceArn")
        self.glue_backend.delete_resource_policy(
            resource_arn=resource_arn,
            policy_hash_condition=policy_hash_condition,
        )

        return EmptyResult()

    def create_workflow(self) -> ActionResult:
        name = self._get_param("Name")
        default_run_properties = self._get_param("DefaultRunProperties")
        description = self._get_param("Description")
        max_concurrent_runs = self._get_int_param("MaxConcurrentRuns")
        tags = self._get_param("Tags")

        workflow_name = self.glue_backend.create_workflow(
            name,
            default_run_properties,
            description,
            max_concurrent_runs,
            tags,
        )
        return ActionResult({"Name": workflow_name})

    def get_workflow(self) -> ActionResult:
        name = self._get_param("Name")

        workflow = self.glue_backend.get_workflow(name)
        return ActionResult({"Workflow": workflow})

    def list_workflows(self) -> ActionResult:
        workflows = self.glue_backend.list_workflows()
        return PaginatedResult({"Workflows": workflows})

    def batch_get_workflows(self) -> ActionResult:
        names = self._get_param("Names")
        workflows = []
        missing_workflows = []

        for name in names:
            try:
                workflow = self.glue_backend.get_workflow(name)
                workflows.append(workflow)
            except EntityNotFoundException:
                missing_workflows.append(name)

        return ActionResult(
            {"MissingWorkflows": missing_workflows, "Workflows": workflows}
        )

    def update_workflow(self) -> ActionResult:
        name = self._get_param("Name")
        default_run_properties = self._get_param("DefaultRunProperties")
        description = self._get_param("Description")
        max_concurrent_runs = self._get_int_param("MaxConcurrentRuns")

        name = self.glue_backend.update_workflow(
            name,
            default_run_properties,
            description,
            max_concurrent_runs,
        )

        return ActionResult({"Name": name})

    def delete_workflow(self) -> ActionResult:
        name = self._get_param("Name")
        name = self.glue_backend.delete_workflow(name)

        return ActionResult({"Name": name})

    def get_workflow_run(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        run_id = self._get_param("RunId")

        workflow_run = self.glue_backend.get_workflow_run(workflow_name, run_id)
        return ActionResult({"Run": workflow_run})

    def get_workflow_runs(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        workflow_runs = self.glue_backend.get_workflow_runs(workflow_name)
        return PaginatedResult({"Runs": workflow_runs})

    def start_workflow_run(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        properties = self._get_param("RunProperties")

        run_id = self.glue_backend.start_workflow_run(workflow_name, properties)
        return ActionResult({"RunId": run_id})

    def stop_workflow_run(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        run_id = self._get_param("RunId")

        self.glue_backend.stop_workflow_run(workflow_name, run_id)
        return EmptyResult()

    def get_workflow_run_properties(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        run_id = self._get_param("RunId")

        run_properties = self.glue_backend.get_workflow_run_properties(
            workflow_name, run_id
        )
        return ActionResult({"RunProperties": run_properties})

    def put_workflow_run_properties(self) -> ActionResult:
        workflow_name = self._get_param("Name")
        run_id = self._get_param("RunId")
        run_properties = self._get_param("RunProperties")

        self.glue_backend.put_workflow_run_properties(
            workflow_name, run_id, run_properties
        )
        return EmptyResult()

    def create_security_configuration(self) -> ActionResult:
        name = self._get_param("Name")
        configuration = self._get_param("EncryptionConfiguration")

        sc = self.glue_backend.create_security_configuration(name, configuration)
        return ActionResult({"Name": sc.name, "CreatedTimestamp": sc.created_time})

    def get_security_configuration(self) -> ActionResult:
        name = self._get_param("Name")
        security_configuration = self.glue_backend.get_security_configuration(name)
        return ActionResult({"SecurityConfiguration": security_configuration.as_dict()})

    def delete_security_configuration(self) -> ActionResult:
        name = self._get_param("Name")
        self.glue_backend.delete_security_configuration(name)
        return EmptyResult()

    def get_security_configurations(self) -> ActionResult:
        security_configurations = self.glue_backend.get_security_configurations()
        return PaginatedResult(
            {"SecurityConfigurations": [sc.as_dict() for sc in security_configurations]}
        )
