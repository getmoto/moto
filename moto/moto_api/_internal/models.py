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
        query_execution_id: str,
        rows: List[Dict[str, Any]],
        column_info: Optional[List[Dict[str, str]]] = None,
        region: str = "us-east-1",
    ) -> None:
        from moto.athena.models import athena_backends, QueryResults

        if column_info is None:
            column_info = []
        backend = athena_backends[DEFAULT_ACCOUNT_ID][region]
        results = QueryResults(rows=rows, column_info=column_info)
        backend.query_results[query_execution_id] = results


moto_api_backend = MotoAPIBackend(region_name="global", account_id=DEFAULT_ACCOUNT_ID)
