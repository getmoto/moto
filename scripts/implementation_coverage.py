#!/usr/bin/env python
import moto
import os
from botocore import xform_name
from botocore.session import Session
import boto3


script_dir = os.path.dirname(os.path.abspath(__file__))


def get_moto_implementation(service_name):
    service_name_standardized = service_name.replace("-", "") if "-" in service_name else service_name
    if not hasattr(moto, service_name_standardized):
        return None
    module = getattr(moto, service_name_standardized)
    if module is None:
        return None
    mock = getattr(module, "mock_{}".format(service_name_standardized))
    if mock is None:
        return None
    backends = list(mock().backends.values())
    if backends:
        return backends[0]


def calculate_implementation_coverage():
    service_names = Session().get_available_services()
    coverage = {}
    for service_name in service_names:
        moto_client = get_moto_implementation(service_name)
        real_client = boto3.client(service_name, region_name='us-east-1')
        implemented = []
        not_implemented = []

        operation_names = [xform_name(op) for op in real_client.meta.service_model.operation_names]
        for op in operation_names:
            if moto_client and op in dir(moto_client):
                implemented.append(op)
            else:
                not_implemented.append(op)

        coverage[service_name] = {
            'implemented': implemented,
            'not_implemented': not_implemented,
        }
    return coverage


def print_implementation_coverage(coverage):
    for service_name in sorted(coverage):
        implemented = coverage.get(service_name)['implemented']
        not_implemented = coverage.get(service_name)['not_implemented']
        operations = sorted(implemented + not_implemented)

        if implemented and not_implemented:
            percentage_implemented = int(100.0 * len(implemented) / (len(implemented) + len(not_implemented)))
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
    # try deleting the implementation coverage file
    try:
        os.remove("../IMPLEMENTATION_COVERAGE.md")
    except OSError:
        pass

    implementation_coverage_file = "{}/../IMPLEMENTATION_COVERAGE.md".format(script_dir)
    # rewrite the implementation coverage file with updated values
    print("Writing to {}".format(implementation_coverage_file))
    with open(implementation_coverage_file, "a+") as file:
        for service_name in sorted(coverage):
            implemented = coverage.get(service_name)['implemented']
            not_implemented = coverage.get(service_name)['not_implemented']
            operations = sorted(implemented + not_implemented)

            if implemented and not_implemented:
                percentage_implemented = int(100.0 * len(implemented) / (len(implemented) + len(not_implemented)))
            elif implemented:
                percentage_implemented = 100
            else:
                percentage_implemented = 0

            file.write("\n")
            file.write("## {}\n".format(service_name))
            file.write("{}% implemented\n".format(percentage_implemented))
            for op in operations:
                if op in implemented:
                    file.write("- [X] {}\n".format(op))
                else:
                    file.write("- [ ] {}\n".format(op))


if __name__ == '__main__':
    cov = calculate_implementation_coverage()
    write_implementation_coverage_to_file(cov)
    print_implementation_coverage(cov)
