from moto.core import BaseBackend
from moto.ec2 import ec2_backends
from moto.sts.models import ACCOUNT_ID

class FakeSagemakerNotebookInstance:
    def __init__(self, name, instance_type, execution_role, region_name):
        self.name = name
        self.instance_type = instance_type
        self.execution_role = execution_role
        self.region_name = region_name
        # ToDo: Validate these params.  Raise if bad.

    @property
    def arn(self):
        return (
            "arn:aws:sagemaker:"
            + self.region_name
            + ":"
            + str(ACCOUNT_ID)
            + ":notebook-instance/"
            + self.name
        )


class SageMakerBackend(BaseBackend):
    def __init__(self, region_name=None):
        self.notebook_instances = {}
        self.region_name = region_name

    def reset(self):
        region_name = self.region_name
        super().reset()
        self.region_name = region_name

    def create_notebook_instance(self, name, instance_type, execution_role):
        # if name in self.notebook_instances:
        #     raise Exception("Notebook Instance named {name} already exists")
        notebook_instance = FakeSagemakerNotebookInstance(name, instance_type, execution_role, self.region_name)
        self.notebook_instances[name] = notebook_instance
        return notebook_instance


sagemaker_backends = {}
for region, ec2_backend in ec2_backends.items():
    sagemaker_backends[region] = SageMakerBackend(region)