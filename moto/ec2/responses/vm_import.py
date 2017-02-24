from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class VMImport(BaseResponse):

    def cancel_conversion_task(self):
        raise NotImplementedError(
            'VMImport.cancel_conversion_task is not yet implemented')

    def describe_conversion_tasks(self):
        raise NotImplementedError(
            'VMImport.describe_conversion_tasks is not yet implemented')

    def import_instance(self):
        raise NotImplementedError(
            'VMImport.import_instance is not yet implemented')

    def import_volume(self):
        raise NotImplementedError(
            'VMImport.import_volume is not yet implemented')
