#!/usr/bin/env python
"""Download markdown files with AWS managed ConfigRule info and convert to JSON.

Invocation:  ./pull_down_aws_managed_rules.py
    - Execute from the moto/scripts directory.
    - To track download progress, use the "-v" command line switch.
    - MANAGED_RULES_OUTPUT_FILENAME is the variable containing the name of
      the file that will be overwritten when this script is run.

    NOTE:  This script takes a while to download all the files.

Summary:
    The first markdown file is read to obtain the names of markdown files
    for all the AWS managed config rules.  Then each of those markdown files
    are read and info is extracted with the final results written to a JSON
    file.

    The JSON output will look as follows:

    {
        "ManagedRules": [
            {
                "ACCESS_KEYS_ROTATED": {
                    "AWS Region": "All supported AWS regions",
                    "Parameters": [
                        {
                            "Default": "90",
                            "Name": "maxAccessKeyAgeType",
                            "Optional": false,
                            "Type": "intDefault"
                            }
                    ],
                    "Trigger type": "Periodic"
                },
            },
            ...
        ]
    }
"""
import argparse

import json
import re
import sys

import requests

MANAGED_RULES_OUTPUT_FILENAME = "../moto/config/resources/aws_managed_rules.json"

AWS_MARKDOWN_URL_START = "https://raw.githubusercontent.com/awsdocs/aws-config-developer-guide/main/doc_source/"

LIST_OF_MARKDOWNS_URL = "managed-rules-by-aws-config.md"


def extract_param_info(line):
    """Return dict containing parameter info extracted from line."""
    # Examples of parameter definitions:
    #   maxAccessKeyAgeType: intDefault: 90
    #   IgnorePublicAcls \(Optional\)Type: StringDefault: True
    #   MasterAccountId \(Optional\)Type: String
    #   endpointConfigurationTypesType: String

    values = re.split(r":\s?", line)
    name = values[0]
    param_type = values[1]

    # If there is no Optional keyword, then sometimes there
    # isn't a space between the parameter name and "Type".
    name = re.sub("Type$", "", name)

    # Sometimes there isn't a space between the type and the
    # word "Default".
    if "Default" in param_type:
        param_type = re.sub("Default$", "", param_type)

    optional = False
    if "Optional" in line:
        optional = True
        # Remove "Optional" from the line.
        name = name.split()[0]

    param_info = {
        "Name": name,
        "Optional": optional,
        "Type": param_type,
    }

    # A default value isn't always provided.
    if len(values) > 2:
        param_info["Default"] = values[2]

    return param_info


def extract_managed_rule_info(lines):
    """Return dict of qualifiers/rules extracted from a markdown file."""
    rule_info = {}
    label_pattern = re.compile(r"(?:\*\*)(?P<label>[^\*].*)\:\*\*\s?(?P<value>.*)?")

    collecting_params = False
    params = []
    for line in lines:
        if not line:
            continue
        line = line.replace("\\", "").strip()

        # Parameters are listed in the lines following the label, so they
        # require special processing.
        if collecting_params:
            # A new header marks the end of the parameters.
            if line.startswith("##"):
                rule_info["Parameters"] = params
                break

            if "Type: " in line:
                params.append(extract_param_info(line))
            continue

        # Check for a label starting with two asterisks.
        matches = re.match(label_pattern, line)
        if not matches:
            continue

        # Look for "Identifier", "Trigger type", "AWS Region" and
        # "Parameters" labels and store the values for all but parameters.
        # Parameters values aren't on the same line as labels.
        label = matches.group("label")
        value = matches.group("value")
        if label in ["Identifier", "Trigger type", "AWS Region"]:
            rule_info[label] = value
        elif label == "Parameters":
            collecting_params = True
        else:
            print(f"ERROR:  Unknown label: '{label}', line: '{line}'", file=sys.stderr)
    return rule_info


def process_cmdline_args():
    """Return parsed command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            f"Download AWS config rules and merge output to create the "
            f"JSON file {MANAGED_RULES_OUTPUT_FILENAME}"
        )
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Report on progress of downloads"
    )
    return parser.parse_args()


def main():
    """Create a JSON file containing info pulled from AWS markdown files."""
    args = process_cmdline_args()

    # Get the markdown file with links to the markdown files for services.
    req = requests.get(AWS_MARKDOWN_URL_START + LIST_OF_MARKDOWNS_URL)

    # Extract the list of all the markdown files on the page.
    link_pattern = re.compile(r"\+ \[[^\]]+\]\(([^)]+)\)")
    markdown_files = link_pattern.findall(req.text)

    # For each of those markdown files, extract the id, region, trigger type
    # and parameter information.
    managed_rules = {"ManagedRules": {}}
    for markdown_file in markdown_files:
        if args.verbose:
            print(f"Downloading {markdown_file} ...")
        req = requests.get(AWS_MARKDOWN_URL_START + markdown_file)
        rules = extract_managed_rule_info(req.text.split("\n"))

        rule_id = rules.pop("Identifier")
        managed_rules["ManagedRules"][rule_id] = rules

    # Create a JSON file with the extracted managed rule info.
    with open(MANAGED_RULES_OUTPUT_FILENAME, "w", encoding="utf-8") as fhandle:
        json.dump(managed_rules, fhandle, sort_keys=True, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
