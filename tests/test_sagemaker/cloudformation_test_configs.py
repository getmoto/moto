import json
from abc import ABCMeta, abstractmethod

from moto.sts.models import ACCOUNT_ID


class TestConfig(metaclass=ABCMeta):
    """Provides the interface to use for creating test configurations.

    This class will provide the interface for what information will be
    needed for the SageMaker CloudFormation tests. Ultimately, this will
    improve the readability of the tests in `test_sagemaker_cloudformation.py`
    because it will reduce the amount of information we pass through the
    `pytest.mark.parametrize` decorator.

    """

    @property
    @abstractmethod
    def resource_name(self):
        pass

    @property
    @abstractmethod
    def describe_function_name(self):
        pass

    @property
    @abstractmethod
    def name_parameter(self):
        pass

    @property
    @abstractmethod
    def arn_parameter(self):
        pass

    @abstractmethod
    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        pass


class NotebookInstanceTestConfig(TestConfig):
    """Test configuration for SageMaker Notebook Instances."""

    @property
    def resource_name(self):
        return "TestNotebook"

    @property
    def describe_function_name(self):
        return "describe_notebook_instance"

    @property
    def name_parameter(self):
        return "NotebookInstanceName"

    @property
    def arn_parameter(self):
        return "NotebookInstanceArn"

    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        instance_type = kwargs.get("instance_type", "ml.c4.xlarge")
        role_arn = kwargs.get(
            "role_arn", "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
        )

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                self.resource_name: {
                    "Type": "AWS::SageMaker::NotebookInstance",
                    "Properties": {"InstanceType": instance_type, "RoleArn": role_arn},
                },
            },
        }
        if include_outputs:
            template["Outputs"] = {
                "Arn": {"Value": {"Ref": self.resource_name}},
                "Name": {
                    "Value": {
                        "Fn::GetAtt": [self.resource_name, "NotebookInstanceName"]
                    }
                },
            }
        return json.dumps(template)


class NotebookInstanceLifecycleConfigTestConfig(TestConfig):
    """Test configuration for SageMaker Notebook Instance Lifecycle Configs."""

    @property
    def resource_name(self):
        return "TestNotebookLifecycleConfig"

    @property
    def describe_function_name(self):
        return "describe_notebook_instance_lifecycle_config"

    @property
    def name_parameter(self):
        return "NotebookInstanceLifecycleConfigName"

    @property
    def arn_parameter(self):
        return "NotebookInstanceLifecycleConfigArn"

    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        on_create = kwargs.get("on_create")
        on_start = kwargs.get("on_start")

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                self.resource_name: {
                    "Type": "AWS::SageMaker::NotebookInstanceLifecycleConfig",
                    "Properties": {},
                },
            },
        }
        if on_create is not None:
            template["Resources"][self.resource_name]["Properties"]["OnCreate"] = [
                {"Content": on_create}
            ]
        if on_start is not None:
            template["Resources"][self.resource_name]["Properties"]["OnStart"] = [
                {"Content": on_start}
            ]
        if include_outputs:
            template["Outputs"] = {
                "Arn": {"Value": {"Ref": self.resource_name}},
                "Name": {
                    "Value": {
                        "Fn::GetAtt": [
                            self.resource_name,
                            "NotebookInstanceLifecycleConfigName",
                        ]
                    }
                },
            }
        return json.dumps(template)
