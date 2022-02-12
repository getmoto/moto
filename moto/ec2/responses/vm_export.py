from moto.core.responses import BaseResponse


class VMExport(BaseResponse):
    def cancel_export_task(self):
        raise NotImplementedError("VMExport.cancel_export_task is not yet implemented")

    def create_instance_export_task(self):
        raise NotImplementedError(
            "VMExport.create_instance_export_task is not yet implemented"
        )

    def describe_export_tasks(self):
        raise NotImplementedError(
            "VMExport.describe_export_tasks is not yet implemented"
        )
