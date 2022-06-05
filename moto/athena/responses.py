import json

from moto.core.responses import BaseResponse
from .models import athena_backends


class AthenaResponse(BaseResponse):
    @property
    def athena_backend(self):
        return athena_backends[self.get_current_account()][self.region]

    def create_work_group(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        configuration = self._get_param("Configuration")
        tags = self._get_param("Tags")
        work_group = self.athena_backend.create_work_group(
            name, configuration, description, tags
        )
        if not work_group:
            return self.error("WorkGroup already exists", 400)
        return json.dumps(
            {
                "CreateWorkGroupResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384ac68d-3775-11df-8963-01868b7c937a"
                    }
                }
            }
        )

    def list_work_groups(self):
        return json.dumps({"WorkGroups": self.athena_backend.list_work_groups()})

    def get_work_group(self):
        name = self._get_param("WorkGroup")
        return json.dumps({"WorkGroup": self.athena_backend.get_work_group(name)})

    def start_query_execution(self):
        query = self._get_param("QueryString")
        context = self._get_param("QueryExecutionContext")
        config = self._get_param("ResultConfiguration")
        workgroup = self._get_param("WorkGroup")
        if workgroup and not self.athena_backend.get_work_group(workgroup):
            return self.error("WorkGroup does not exist", 400)
        q_exec_id = self.athena_backend.start_query_execution(
            query=query, context=context, config=config, workgroup=workgroup
        )
        return json.dumps({"QueryExecutionId": q_exec_id})

    def get_query_execution(self):
        exec_id = self._get_param("QueryExecutionId")
        execution = self.athena_backend.get_execution(exec_id)
        result = {
            "QueryExecution": {
                "QueryExecutionId": exec_id,
                "Query": execution.query,
                "StatementType": "DDL",
                "ResultConfiguration": execution.config,
                "QueryExecutionContext": execution.context,
                "Status": {
                    "State": execution.status,
                    "SubmissionDateTime": execution.start_time,
                },
                "Statistics": {
                    "EngineExecutionTimeInMillis": 0,
                    "DataScannedInBytes": 0,
                    "TotalExecutionTimeInMillis": 0,
                    "QueryQueueTimeInMillis": 0,
                    "QueryPlanningTimeInMillis": 0,
                    "ServiceProcessingTimeInMillis": 0,
                },
                "WorkGroup": execution.workgroup,
            }
        }
        return json.dumps(result)

    def stop_query_execution(self):
        exec_id = self._get_param("QueryExecutionId")
        self.athena_backend.stop_query_execution(exec_id)
        return json.dumps({})

    def error(self, msg, status):
        return (
            json.dumps({"__type": "InvalidRequestException", "Message": msg}),
            dict(status=status),
        )

    def create_named_query(self):
        name = self._get_param("Name")
        description = self._get_param("Description")
        database = self._get_param("Database")
        query_string = self._get_param("QueryString")
        workgroup = self._get_param("WorkGroup")
        if workgroup and not self.athena_backend.get_work_group(workgroup):
            return self.error("WorkGroup does not exist", 400)
        query_id = self.athena_backend.create_named_query(
            name, description, database, query_string, workgroup
        )
        return json.dumps({"NamedQueryId": query_id})

    def get_named_query(self):
        query_id = self._get_param("NamedQueryId")
        nq = self.athena_backend.get_named_query(query_id)
        return json.dumps(
            {
                "NamedQuery": {
                    "Name": nq.name,
                    "Description": nq.description,
                    "Database": nq.database,
                    "QueryString": nq.query_string,
                    "NamedQueryId": nq.id,
                    "WorkGroup": nq.workgroup,
                }
            }
        )

    def list_data_catalogs(self):
        return json.dumps(
            {"DataCatalogsSummary": self.athena_backend.list_data_catalogs()}
        )

    def get_data_catalog(self):
        name = self._get_param("Name")
        return json.dumps({"DataCatalog": self.athena_backend.get_data_catalog(name)})

    def create_data_catalog(self):
        name = self._get_param("Name")
        catalog_type = self._get_param("Type")
        description = self._get_param("Description")
        parameters = self._get_param("Parameters")
        tags = self._get_param("Tags")
        data_catalog = self.athena_backend.create_data_catalog(
            name, catalog_type, description, parameters, tags
        )
        if not data_catalog:
            return self.error("DataCatalog already exists", 400)
        return json.dumps(
            {
                "CreateDataCatalogResponse": {
                    "ResponseMetadata": {
                        "RequestId": "384ac68d-3775-11df-8963-01868b7c937a"
                    }
                }
            }
        )
