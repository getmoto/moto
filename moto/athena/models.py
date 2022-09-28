import time

from moto.core import BaseBackend, BaseModel
from moto.core.utils import BackendDict
from moto.moto_api._internal import mock_random


class TaggableResourceMixin(object):
    # This mixing was copied from Redshift when initially implementing
    # Athena. TBD if it's worth the overhead.

    def __init__(self, account_id, region_name, resource_name, tags):
        self.region = region_name
        self.resource_name = resource_name
        self.tags = tags or []
        self.arn = f"arn:aws:athena:{region_name}:{account_id}:{resource_name}"

    def create_tags(self, tags):
        new_keys = [tag_set["Key"] for tag_set in tags]
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in new_keys]
        self.tags.extend(tags)
        return self.tags

    def delete_tags(self, tag_keys):
        self.tags = [tag_set for tag_set in self.tags if tag_set["Key"] not in tag_keys]
        return self.tags


class WorkGroup(TaggableResourceMixin, BaseModel):

    resource_type = "workgroup"
    state = "ENABLED"

    def __init__(self, athena_backend, name, configuration, description, tags):
        self.region_name = athena_backend.region_name
        super().__init__(
            athena_backend.account_id,
            self.region_name,
            "workgroup/{}".format(name),
            tags,
        )
        self.athena_backend = athena_backend
        self.name = name
        self.description = description
        self.configuration = configuration


class DataCatalog(TaggableResourceMixin, BaseModel):
    def __init__(
        self, athena_backend, name, catalog_type, description, parameters, tags
    ):
        self.region_name = athena_backend.region_name
        super().__init__(
            athena_backend.account_id,
            self.region_name,
            "datacatalog/{}".format(name),
            tags,
        )
        self.athena_backend = athena_backend
        self.name = name
        self.type = catalog_type
        self.description = description
        self.parameters = parameters


class Execution(BaseModel):
    def __init__(self, query, context, config, workgroup):
        self.id = str(mock_random.uuid4())
        self.query = query
        self.context = context
        self.config = config
        self.workgroup = workgroup
        self.start_time = time.time()
        self.status = "QUEUED"


class NamedQuery(BaseModel):
    def __init__(self, name, description, database, query_string, workgroup):
        self.id = str(mock_random.uuid4())
        self.name = name
        self.description = description
        self.database = database
        self.query_string = query_string
        self.workgroup = workgroup


class AthenaBackend(BaseBackend):
    region_name = None

    def __init__(self, region_name, account_id):
        super().__init__(region_name, account_id)
        self.work_groups = {}
        self.executions = {}
        self.named_queries = {}
        self.data_catalogs = {}

    @staticmethod
    def default_vpc_endpoint_service(service_region, zones):
        """Default VPC endpoint service."""
        return BaseBackend.default_vpc_endpoint_service_factory(
            service_region, zones, "athena"
        )

    def create_work_group(self, name, configuration, description, tags):
        if name in self.work_groups:
            return None
        work_group = WorkGroup(self, name, configuration, description, tags)
        self.work_groups[name] = work_group
        return work_group

    def list_work_groups(self):
        return [
            {
                "Name": wg.name,
                "State": wg.state,
                "Description": wg.description,
                "CreationTime": time.time(),
            }
            for wg in self.work_groups.values()
        ]

    def get_work_group(self, name):
        if name not in self.work_groups:
            return None
        wg = self.work_groups[name]
        return {
            "Name": wg.name,
            "State": wg.state,
            "Configuration": wg.configuration,
            "Description": wg.description,
            "CreationTime": time.time(),
        }

    def start_query_execution(self, query, context, config, workgroup):
        execution = Execution(
            query=query, context=context, config=config, workgroup=workgroup
        )
        self.executions[execution.id] = execution
        return execution.id

    def get_execution(self, exec_id):
        return self.executions[exec_id]

    def stop_query_execution(self, exec_id):
        execution = self.executions[exec_id]
        execution.status = "CANCELLED"

    def create_named_query(self, name, description, database, query_string, workgroup):
        nq = NamedQuery(
            name=name,
            description=description,
            database=database,
            query_string=query_string,
            workgroup=workgroup,
        )
        self.named_queries[nq.id] = nq
        return nq.id

    def get_named_query(self, query_id):
        return self.named_queries[query_id] if query_id in self.named_queries else None

    def list_data_catalogs(self):
        return [
            {"CatalogName": dc.name, "Type": dc.type}
            for dc in self.data_catalogs.values()
        ]

    def get_data_catalog(self, name):
        if name not in self.data_catalogs:
            return None
        dc = self.data_catalogs[name]
        return {
            "Name": dc.name,
            "Description": dc.description,
            "Type": dc.type,
            "Parameters": dc.parameters,
        }

    def create_data_catalog(self, name, catalog_type, description, parameters, tags):
        if name in self.data_catalogs:
            return None
        data_catalog = DataCatalog(
            self, name, catalog_type, description, parameters, tags
        )
        self.data_catalogs[name] = data_catalog
        return data_catalog


athena_backends = BackendDict(AthenaBackend, "athena")
