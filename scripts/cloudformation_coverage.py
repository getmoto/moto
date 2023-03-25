#!/usr/bin/env python
import importlib
import json
import mock
import requests

import moto

# Populate CloudFormationModel.__subclasses__()
moto.mock_all()


def check(condition):
    if bool(condition):
        return "x"
    else:
        return " "


def is_implemented(model, method_name):
    # method_name in model.__dict__ will be True if the method
    # exists on the model and False if it's only inherited from
    # CloudFormationModel.
    return hasattr(model, method_name) and method_name in model.__dict__


class CloudFormationChecklist:
    def __init__(self, resource_name, schema):
        self.resource_name = resource_name
        self.schema = schema

    def __str__(self):
        missing_attrs_checklist = "\n".join(
            [f"      - [ ] {attr}" for attr in self.missing_attrs]
        )
        report = (
            f"- {self.resource_name}:\n"
            f"   - [{check(self.creatable)}] create implemented\n"
            f"   - [{check(self.updatable)}] update implemented\n"
            f"   - [{check(self.deletable)}] delete implemented\n"
            f"   - [{check(not self.missing_attrs)}] Fn::GetAtt implemented\n"
        ) + missing_attrs_checklist

        return report.strip()

    @property
    def service_name(self):
        return self.resource_name.split("::")[1].lower()

    @property
    def model_name(self):
        return self.resource_name.split("::")[2]

    @property
    def moto_model(self):
        for subclass in moto.core.common_models.CloudFormationModel.__subclasses__():
            subclass_service = subclass.__module__.split(".")[1]
            subclass_model = subclass.__name__

            if subclass_service == self.service_name and subclass_model in (
                self.model_name,
                "Fake" + self.model_name,
            ):
                return subclass

    @property
    def expected_attrs(self):
        return list(self.schema.get("Attributes", {}).keys())

    @property
    def missing_attrs(self):
        missing_attrs = []
        for attr in self.expected_attrs:
            try:
                # TODO: Change the actual abstract method to return False
                with mock.patch(
                    "moto.core.common_models.CloudFormationModel.has_cfn_attr",
                    return_value=False,
                ):
                    if not self.moto_model.has_cfn_attr(attr):
                        missing_attrs.append(attr)
            except:
                missing_attrs.append(attr)
        return missing_attrs

    @property
    def creatable(self):
        return is_implemented(self.moto_model, "create_from_cloudformation_json")

    @property
    def updatable(self):
        return is_implemented(self.moto_model, "update_from_cloudformation_json")

    @property
    def deletable(self):
        return is_implemented(self.moto_model, "delete_from_cloudformation_json")


if __name__ == "__main__":
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html
    cfn_spec = requests.get(
        "https://dnwj8swjjbsbt.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"
    ).json()
    for resource_name, schema in sorted(cfn_spec["ResourceTypes"].items()):
        checklist = CloudFormationChecklist(resource_name, schema)
        # Only print checklists for models that implement CloudFormationModel;
        # otherwise the checklist is very long and mostly empty because there
        # are so many niche AWS services and resources that moto doesn't
        # implement yet.
        if checklist.moto_model:
            print(checklist)
