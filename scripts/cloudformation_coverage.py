#!/usr/bin/env python
from unittest.mock import patch
import requests
import os

import moto

# Populate CloudFormationModel.__subclasses__()
moto.mock_all()


script_dir = os.path.dirname(os.path.abspath(__file__))


def check(condition):
    if bool(condition):
        return "x"
    else:
        return " "


def utf_checkbox(condition):
    return "☑" if bool(condition) else " "


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
                with patch(
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


def write_main_document(supported):
    implementation_coverage_file = "{}/../CLOUDFORMATION_COVERAGE.md".format(script_dir)
    try:
        os.remove(implementation_coverage_file)
    except OSError:
        pass

    print("Writing to {}".format(implementation_coverage_file))
    with open(implementation_coverage_file, "w+") as file:
        file.write("## Supported CloudFormation resources")
        file.write("\n\n")
        file.write("A list of all resources that can be created via CloudFormation. \n")
        file.write("Please let us know if you'd like support for a resource not yet listed here.")
        file.write("\n\n")

        for checklist in supported:
            file.write(str(checklist))
            file.write("\n")


def write_documentation(supported):
    docs_file = "{}/../docs/docs/services/cf.rst".format(script_dir)
    try:
        os.remove(docs_file)
    except OSError:
        pass

    print("Writing to {}".format(docs_file))
    with open(docs_file, "w+") as file:
        file.write(f".. _cloudformation_resources:\n")
        file.write("\n")
        file.write("==================================\n")
        file.write("Supported CloudFormation resources\n")
        file.write("==================================\n")
        file.write("\n\n")
        file.write("A list of all resources that can be created via CloudFormation. \n")
        file.write("Please let us know if you'd like support for a resource not yet listed here.")
        file.write("\n\n")

        max_resource_name_length = max([len(cf.resource_name) for cf in supported]) + 2
        max_fn_att_length = 35

        file.write(".. table:: \n\n")
        file.write(f"  +{('-'*max_resource_name_length)}+--------+--------+--------+{('-' * max_fn_att_length)}+\n")
        file.write(f"  |{(' '*max_resource_name_length)}| Create | Update | Delete | {('Fn::GetAtt'.ljust(max_fn_att_length-2))} |\n")
        file.write(f"  +{('='*max_resource_name_length)}+========+========+========+{('=' * max_fn_att_length)}+\n")

        for checklist in supported:
            attrs = [f" - [{check(att not in checklist.missing_attrs)}] {att}" for att in checklist.expected_attrs]
            first_attr = attrs[0] if attrs else ""
            file.write("  |")
            file.write(checklist.resource_name.ljust(max_resource_name_length))
            file.write("|")
            file.write(f"    {check(checklist.creatable)}   ")
            file.write("|")
            file.write(f"    {check(checklist.updatable)}   ")
            file.write("|")
            file.write(f"    {check(checklist.deletable)}   ")
            file.write(f"|{first_attr.ljust(max_fn_att_length)}|")
            file.write("\n")
            for index, attr in enumerate(attrs[1:]):
                if index % 2 == 0:
                    file.write(
                        f"  +{('-' * max_resource_name_length)}+--------+--------+--------+{attr.ljust(max_fn_att_length)}|\n")
                else:
                    file.write(
                        f"  |{(' ' * max_resource_name_length)}|        |        |        |{attr.ljust(max_fn_att_length)}|\n")
            if len(attrs) > 1 and len(attrs) % 2 == 0:
                file.write(f"  |{(' ' * max_resource_name_length)}|        |        |        |{(' ' * max_fn_att_length)}|\n")
            file.write(f"  +{('-'*max_resource_name_length)}+--------+--------+--------+{('-' * max_fn_att_length)}+\n")


if __name__ == "__main__":
    # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-resource-specification.html
    cfn_spec = requests.get(
        "https://dnwj8swjjbsbt.cloudfront.net/latest/gzip/CloudFormationResourceSpecification.json"
    ).json()
    # Only collect checklists for models that implement CloudFormationModel;
    # otherwise the checklist is very long and mostly empty because there
    # are so many niche AWS services and resources that moto doesn't implement yet.
    supported = [CloudFormationChecklist(resource_name, schema) for resource_name, schema in sorted(cfn_spec["ResourceTypes"].items()) if CloudFormationChecklist(resource_name, schema).moto_model]
    #write_main_document(supported)
    write_documentation(supported)
