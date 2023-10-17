from moto.core import BaseBackend, DEFAULT_ACCOUNT_ID
from moto.core.model_instances import reset_model_data
from typing import Any, Dict, List, Optional


class MotoAPIBackend(BaseBackend):
    def reset(self) -> None:
        region_name = self.region_name
        account_id = self.account_id

        import moto.backends as backends

        for name, backends_ in backends.loaded_backends():
            if name == "moto_api":
                continue
            for backend in backends_.values():
                backend.reset()
        reset_model_data()
        self.__init__(region_name, account_id)  # type: ignore[misc]

    def get_transition(self, model_name: str) -> Dict[str, Any]:
        from moto.moto_api import state_manager

        return state_manager.get_transition(model_name)

    def set_transition(self, model_name: str, transition: Dict[str, Any]) -> None:
        from moto.moto_api import state_manager

        state_manager.set_transition(model_name, transition)

    def unset_transition(self, model_name: str) -> None:
        from moto.moto_api import state_manager

        state_manager.unset_transition(model_name)

    def set_athena_result(
        self,
        rows: List[Dict[str, Any]],
        column_info: List[Dict[str, str]],
        account_id: str,
        region: str,
    ) -> None:
        from moto.athena.models import athena_backends, QueryResults

        backend = athena_backends[account_id][region]
        results = QueryResults(rows=rows, column_info=column_info)
        backend.query_results_queue.append(results)

    def set_sagemaker_result(
        self,
        body: str,
        content_type: str,
        prod_variant: str,
        custom_attrs: str,
        account_id: str,
        region: str,
    ) -> None:
        from moto.sagemakerruntime.models import sagemakerruntime_backends

        backend = sagemakerruntime_backends[account_id][region]
        backend.results_queue.append((body, content_type, prod_variant, custom_attrs))

    def set_rds_data_result(
        self,
        records: Optional[List[List[Dict[str, Any]]]],
        column_metadata: Optional[List[Dict[str, Any]]],
        nr_of_records_updated: Optional[int],
        generated_fields: Optional[List[Dict[str, Any]]],
        formatted_records: Optional[str],
        account_id: str,
        region: str,
    ) -> None:
        from moto.rdsdata.models import rdsdata_backends, QueryResults

        backend = rdsdata_backends[account_id][region]
        backend.results_queue.append(
            QueryResults(
                records=records,
                column_metadata=column_metadata,
                number_of_records_updated=nr_of_records_updated,
                generated_fields=generated_fields,
                formatted_records=formatted_records,
            )
        )

    def set_inspector2_findings_result(
        self,
        results: Optional[List[List[Dict[str, Any]]]],
        account_id: str,
        region: str,
    ) -> None:
        from moto.inspector2.models import inspector2_backends

        backend = inspector2_backends[account_id][region]
        backend.findings_queue.append(results)


moto_api_backend = MotoAPIBackend(region_name="global", account_id=DEFAULT_ACCOUNT_ID)
