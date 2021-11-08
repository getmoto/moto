#!/usr/bin/env python
import moto
import os
from botocore import xform_name
from botocore.session import Session
import boto3


script_dir = os.path.dirname(os.path.abspath(__file__))
alternative_service_names = {"lambda": "awslambda", "dynamodb": "dynamodb2", "rds": "rds2"}


def get_moto_implementation(service_name):
    service_name = (
        service_name.replace("-", "") if "-" in service_name else service_name
    )
    alt_service_name = (
        alternative_service_names[service_name]
        if service_name in alternative_service_names
        else service_name
    )
    if hasattr(moto, "mock_{}".format(alt_service_name)):
        mock = getattr(moto, "mock_{}".format(alt_service_name))
    elif hasattr(moto, "mock_{}".format(service_name)):
        mock = getattr(moto, "mock_{}".format(service_name))
    else:
        mock = None
    if mock is None:
        return None
    backends = list(mock().backends.values())
    if backends:
        return backends[0]


def calculate_extended_implementation_coverage():
    service_names = Session().get_available_services()
    coverage = {}
    for service_name in service_names:
        moto_client = get_moto_implementation(service_name)
        real_client = boto3.client(service_name, region_name="us-east-1")
        implemented = dict()
        not_implemented = []

        operation_names = [
            xform_name(op) for op in real_client.meta.service_model.operation_names
        ]
        for op in operation_names:
            if moto_client and op in dir(moto_client):
                implemented[op] = getattr(moto_client, op)
            else:
                not_implemented.append(op)

        coverage[service_name] = {
            "docs": moto_client.__doc__,
            "implemented": implemented,
            "not_implemented": not_implemented,
        }
    return coverage


def calculate_implementation_coverage():
    service_names = Session().get_available_services()
    coverage = {}
    for service_name in service_names:
        moto_client = get_moto_implementation(service_name)
        real_client = boto3.client(service_name, region_name="us-east-1")
        implemented = []
        not_implemented = []

        operation_names = [
            xform_name(op) for op in real_client.meta.service_model.operation_names
        ]
        for op in operation_names:
            if moto_client and op in dir(moto_client):
                implemented.append(op)
            else:
                not_implemented.append(op)

        coverage[service_name] = {
            "implemented": implemented,
            "not_implemented": not_implemented,
        }
    return coverage


def print_implementation_coverage(coverage):
    for service_name in sorted(coverage):
        implemented = coverage.get(service_name)["implemented"]
        not_implemented = coverage.get(service_name)["not_implemented"]
        operations = sorted(implemented + not_implemented)

        if implemented and not_implemented:
            percentage_implemented = int(
                100.0 * len(implemented) / (len(implemented) + len(not_implemented))
            )
        elif implemented:
            percentage_implemented = 100
        else:
            percentage_implemented = 0

        print("")
        print("## {}\n".format(service_name))
        print("{}% implemented\n".format(percentage_implemented))
        for op in operations:
            if op in implemented:
                print("- [X] {}".format(op))
            else:
                print("- [ ] {}".format(op))


def write_implementation_coverage_to_file(coverage):
    implementation_coverage_file = "{}/../IMPLEMENTATION_COVERAGE.md".format(script_dir)
    # rewrite the implementation coverage file with updated values
    # try deleting the implementation coverage file
    try:
        os.remove(implementation_coverage_file)
    except OSError:
        pass

    print("Writing to {}".format(implementation_coverage_file))
    with open(implementation_coverage_file, "w+") as file:
        completely_unimplemented = []
        for service_name in sorted(coverage):
            implemented = coverage.get(service_name)["implemented"]
            if len(implemented) == 0:
                completely_unimplemented.append(service_name)
                continue
            not_implemented = coverage.get(service_name)["not_implemented"]
            operations = sorted(implemented + not_implemented)

            if implemented and not_implemented:
                percentage_implemented = int(
                    100.0 * len(implemented) / (len(implemented) + len(not_implemented))
                )
            elif implemented:
                percentage_implemented = 100
            else:
                percentage_implemented = 0

            file.write("\n")
            file.write("## {}\n".format(service_name))
            file.write("<details>\n")
            file.write(
                "<summary>{}% implemented</summary>\n\n".format(percentage_implemented)
            )
            for op in operations:
                if op in implemented:
                    file.write("- [X] {}\n".format(op))
                else:
                    file.write("- [ ] {}\n".format(op))
            file.write("</details>\n")

        file.write("\n")
        file.write("## Unimplemented:\n")
        file.write("<details>\n\n")
        for service in completely_unimplemented:
            file.write("- {}\n".format(service))
        file.write("</details>")


def write_implementation_coverage_to_docs(coverage):
    implementation_coverage_file = "{}/../docs/docs/services/index.rst".format(script_dir)
    # rewrite the implementation coverage file with updated values
    # try deleting the implementation coverage file
    try:
        os.remove(implementation_coverage_file)
    except OSError:
        pass

    print("Writing to {}".format(implementation_coverage_file))
    completely_unimplemented = []
    for service_name in sorted(coverage):
        implemented = coverage.get(service_name)["implemented"]
        if len(implemented) == 0:
            completely_unimplemented.append(service_name)
            continue
        not_implemented = coverage.get(service_name)["not_implemented"]
        operations = sorted(list(implemented.keys()) + not_implemented)

        service_coverage_file = "{}/../docs/docs/services/{}.rst".format(script_dir, service_name)
        shorthand = service_name.replace(" ", "_")

        with open(service_coverage_file, "w+") as file:
            file.write(f".. _implementedservice_{shorthand}:\n")
            file.write("\n")

            title = f"{service_name}"
            file.write("=" * len(title) + "\n")
            file.write(title + "\n")
            file.write(("=" * len(title)) + "\n")
            file.write("\n")

            file.write(coverage[service_name].get("docs") or "")
            file.write("\n\n")

            for op in operations:
                if op in implemented:
                    file.write("- [X] {}\n".format(op))
                    docs = getattr(implemented[op], "__doc__")
                    if docs:
                        file.write(f"  {docs}\n\n")
                else:
                    file.write("- [ ] {}\n".format(op))
            file.write("\n")

    with open(implementation_coverage_file, "w+") as file:
        file.write(".. _implemented_services:\n")
        file.write("\n")
        file.write("\n")

        file.write("====================\n")
        file.write("Implemented Services\n")
        file.write("====================\n")
        file.write("\n")
        file.write("\n")

        for service_name in sorted(coverage):
            implemented = coverage.get(service_name)["implemented"]
            if len(implemented) == 0:
                continue
            file.write(f" - :doc:`{service_name }`\n")

        file.write("\n")
        file.write(".. toctree::\n")
        file.write("   :hidden:\n")
        file.write("   :glob:\n")
        file.write("\n")
        file.write("   *\n")


if __name__ == "__main__":
    cov = calculate_implementation_coverage()
    write_implementation_coverage_to_file(cov)
    xcov = calculate_extended_implementation_coverage()
    write_implementation_coverage_to_docs(xcov)
