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

    def run_setup_procedure(self, sagemaker_client):
        """Provides a method to set up resources with a SageMaker client.

        Note: This procedure should be called while within a `mock_sagemaker`
        context so that no actual resources are created with the sagemaker_client.
        """
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


class ModelTestConfig(TestConfig):
    """Test configuration for SageMaker Models."""

    @property
    def resource_name(self):
        return "TestModel"

    @property
    def describe_function_name(self):
        return "describe_model"

    @property
    def name_parameter(self):
        return "ModelName"

    @property
    def arn_parameter(self):
        return "ModelArn"

    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        execution_role_arn = kwargs.get(
            "execution_role_arn", "arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID)
        )
        image = kwargs.get(
            "image", "404615174143.dkr.ecr.us-east-2.amazonaws.com/linear-learner:1"
        )

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                self.resource_name: {
                    "Type": "AWS::SageMaker::Model",
                    "Properties": {
                        "ExecutionRoleArn": execution_role_arn,
                        "PrimaryContainer": {"Image": image},
                    },
                },
            },
        }
        if include_outputs:
            template["Outputs"] = {
                "Arn": {"Value": {"Ref": self.resource_name}},
                "Name": {"Value": {"Fn::GetAtt": [self.resource_name, "ModelName"]}},
            }
        return json.dumps(template)


class EndpointConfigTestConfig(TestConfig):
    """Test configuration for SageMaker Endpoint Configs."""

    @property
    def resource_name(self):
        return "TestEndpointConfig"

    @property
    def describe_function_name(self):
        return "describe_endpoint_config"

    @property
    def name_parameter(self):
        return "EndpointConfigName"

    @property
    def arn_parameter(self):
        return "EndpointConfigArn"

    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        num_production_variants = kwargs.get("num_production_variants", 1)

        production_variants = [
            {
                "InitialInstanceCount": 1,
                "InitialVariantWeight": 1,
                "InstanceType": "ml.c4.xlarge",
                "ModelName": self.resource_name,
                "VariantName": "variant-name-{}".format(i),
            }
            for i in range(num_production_variants)
        ]

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                self.resource_name: {
                    "Type": "AWS::SageMaker::EndpointConfig",
                    "Properties": {"ProductionVariants": production_variants},
                },
            },
        }
        if include_outputs:
            template["Outputs"] = {
                "Arn": {"Value": {"Ref": self.resource_name}},
                "Name": {
                    "Value": {"Fn::GetAtt": [self.resource_name, "EndpointConfigName"]}
                },
            }
        return json.dumps(template)

    def run_setup_procedure(self, sagemaker_client):
        """Adds Model that can be referenced in the CloudFormation template."""

        sagemaker_client.create_model(
            ModelName=self.resource_name,
            ExecutionRoleArn="arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID),
            PrimaryContainer={
                "Image": "404615174143.dkr.ecr.us-east-2.amazonaws.com/linear-learner:1",
            },
        )


class EndpointTestConfig(TestConfig):
    """Test configuration for SageMaker Endpoints."""

    @property
    def resource_name(self):
        return "TestEndpoint"

    @property
    def describe_function_name(self):
        return "describe_endpoint"

    @property
    def name_parameter(self):
        return "EndpointName"

    @property
    def arn_parameter(self):
        return "EndpointArn"

    def get_cloudformation_template(self, include_outputs=True, **kwargs):
        endpoint_config_name = kwargs.get("endpoint_config_name", self.resource_name)

        template = {
            "AWSTemplateFormatVersion": "2010-09-09",
            "Resources": {
                self.resource_name: {
                    "Type": "AWS::SageMaker::Endpoint",
                    "Properties": {"EndpointConfigName": endpoint_config_name},
                },
            },
        }
        if include_outputs:
            template["Outputs"] = {
                "Arn": {"Value": {"Ref": self.resource_name}},
                "Name": {"Value": {"Fn::GetAtt": [self.resource_name, "EndpointName"]}},
            }
        return json.dumps(template)

    def run_setup_procedure(self, sagemaker_client):
        """Adds Model and Endpoint Config that can be referenced in the CloudFormation template."""

        sagemaker_client.create_model(
            ModelName=self.resource_name,
            ExecutionRoleArn="arn:aws:iam::{}:role/FakeRole".format(ACCOUNT_ID),
            PrimaryContainer={
                "Image": "404615174143.dkr.ecr.us-east-2.amazonaws.com/linear-learner:1",
            },
        )
        sagemaker_client.create_endpoint_config(
            EndpointConfigName=self.resource_name,
            ProductionVariants=[
                {
                    "InitialInstanceCount": 1,
                    "InitialVariantWeight": 1,
                    "InstanceType": "ml.c4.xlarge",
                    "ModelName": self.resource_name,
                    "VariantName": "variant-name-1",
                },
            ],
        )
