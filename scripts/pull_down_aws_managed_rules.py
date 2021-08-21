#!/usr/bin/env python
"""Download markdown files with AWS managed ConfigRule info and convert to JSON.

The first markdown file is read to obtain the names of markdown files for
all the AWS managed config rules.  Then each of those markdown files are read
and info is extracted with the final results written to a JSON file.

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
import json
import re
import sys

import requests

MANAGED_RULES_OUTPUT_FILENAME = "../moto/config/resources/aws_managed_rules.json"

AWS_MARKDOWN_URL_START = "https://raw.githubusercontent.com/awsdocs/aws-config-developer-guide/main/doc_source/"

LIST_OF_MARKDOWNS_URL = "managed-rules-by-aws-config.md"


def managed_rule_info(lines):
    """Return dict of qualifiers/rules extracted from a markdown file."""
    rule_info = {}
    label_pattern = re.compile(r"(?:\*\*)(?P<label>[^\*].*)\:\*\*\s?(?P<value>.*)?")

    # Examples of parameter definitions:
    #    maxAccessKeyAgeType: intDefault: 90
    #    IgnorePublicAcls \(Optional\)Type: StringDefault: True
    #    MasterAccountId \(Optional\)Type: String
    #    endpointConfigurationTypesType: String
    #
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

                values_dict = {
                    "Name": name,
                    "Optional": optional,
                    "Type": param_type,
                }

                # A default value isn't always provided.
                if len(values) > 2:
                    values_dict["Default"] = values[2]
                params.append(values_dict)
            continue

        # Check for a label starting with two asterisks.
        matches = re.match(label_pattern, line)
        if not matches:
            continue

        # Look for "Identifier", "Trigger type", "AWS Region" and "Parameters"
        # labels and store the values for all but parameters.  Parameters
        # values aren't on the same line as labels.
        label = matches.group("label")
        value = matches.group("value")
        if label in ["Identifier", "Trigger type", "AWS Region"]:
            rule_info[label] = value.replace("\\", "")
        elif label == "Parameters":
            collecting_params = True
        else:
            print(f"ERROR:  Unknown label: '{label}', line: '{line}'", file=sys.stderr)
    return rule_info


def main():
    """Create a JSON file containing info pulled from AWS markdown files."""
    req = requests.get(AWS_MARKDOWN_URL_START + LIST_OF_MARKDOWNS_URL)

    # Extract the list of all the markdown files on the page.
    link_pattern = re.compile(r"\+ \[[^\]]+\]\(([^)]+)\)")
    markdown_files = link_pattern.findall(req.text)

    markdown = {"ManagedRules": {}}
    for markdown_file in markdown_files:
        req = requests.get(AWS_MARKDOWN_URL_START + markdown_file)
        rules = managed_rule_info(req.text.split("\n"))
        rule_id = rules.pop("Identifier")
        markdown["ManagedRules"][rule_id] = rules

    with open(MANAGED_RULES_OUTPUT_FILENAME, "w") as fhandle:
        json.dump(markdown, fhandle, sort_keys=True, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
