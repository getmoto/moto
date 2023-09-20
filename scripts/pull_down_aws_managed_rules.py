#!/usr/bin/env python
"""Scrape web-based docs for AWS managed ConfigRule info and convert to JSON.

Invocation:  ./pull_down_aws_managed_rules.py
    - Install ../requirements-tests.txt packages to ensure the lxml package
      is installed.
    - Execute from the moto/scripts directory.
    - To track progress, use the "-v" command line switch.
    - MANAGED_RULES_OUTPUT_FILENAME is the variable with the output filename.
      The file is overwritten when this script is successfully run.

    NOTE:  This script takes a while to scrape all the web pages.  The
    scraping could be parallelized, but since this script might only be
    run once every couple of months, it wasn't worth the complexity.

Summary:
    An initial web page is parsed to obtain the links for all the other
    docs for AWS managed config rules.  Each of those links are parsed
    and the needed info is written to a JSON file.

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
                    "Resource type:  "AWS::IAM::User"
                },
            },
            ...
        ]
    }
"""
import argparse

import json
import sys

from lxml import html
import requests

MANAGED_RULES_OUTPUT_FILENAME = "../moto/config/resources/aws_managed_rules.json"

AWS_CONFIG_MANAGED_RULES_URL_START = (
    "https://docs.aws.amazon.com/config/latest/developerguide/"
)

LIST_OF_RULES_URL = "managed-rules-by-aws-config.html"


def extract_param_info(page_content):
    """Return dict containing parameter info extracted from page.

    The info for all (not each) parameters is contained within a "dl" tag,
    with "dt" tags providing the details.  A "dt" tag without a colon
    provides the parameter name and indicates that the "dt" tags that follow
    provide details for that parameter up until the next "dt" tag without a
    colon or the end of the "dl" tag.
    """
    dl_tags = page_content.xpath('//div[@class="variablelist"]//dl')
    if len(dl_tags) > 1:
        print(
            f"ERROR: Found {len(dl_tags)} 'dl' tags for parameters; "
            "only expecting one.  Ignoring extra 'dl' tag.",
            file=sys.stderr
        )

    dt_tags = dl_tags[0].xpath(".//dt")

    all_params = []
    param_details = {}
    for dt_tag in dt_tags:
        text = dt_tag.text_content()
        if not text or text == "None":
            continue

        # If a colon is NOT present, this is the parameter name and not
        # a key, value pair.
        if ": " not in text:
            # If parameter info has been collected, save it and start a
            # collection for this new parameter.
            if param_details:
                all_params.append(param_details)
                param_details = {}
            if "Optional" in text:
                text = text.split()[0]
                param_details["Optional"] = True
            else:
                param_details["Optional"] = False
            param_details["Name"] = text
            continue

        key, value = text.split(": ")
        param_details[key] = value

    # Collect the last parameter found.
    if param_details:
        all_params.append(param_details)

    return all_params


def extract_managed_rule_info(page_content):
    """Return dict of qualifiers/rules extracted from web page.

    An example of the html that's being processed:

    <div id="main-content" class="awsui-util-container">
    ...

    <h1 class="topictitle" id="access-keys-rotated">access-keys-rotated</h1>
    <p><b>Identifier:</b> ACCESS_KEYS_ROTATED</p>
    <p><b>Resource Types:</b> AWS::IAM::User</p>
    <p><b>Trigger type:</b> Periodic</p>
    <p><b>AWS Region:</b> All supported AWS regions except Middle East (UAE),
        Asia Pacific (Hyderabad), Asia Pacific (Melbourne), Israel (Tel Aviv),
        Europe (Spain), Europe (Zurich) Region</p>
    <p><b>Parameters:</b></p>
    <div class="variablelist">
    <dl>
        <dt><span class="term">maxAccessKeyAge</span></dt>
        <dt><span class="term">Type: int</span></dt>
        <dt><span class="term">Default: 90</span></dt>
          <dd>
             <p>Maximum number of days without rotation. Default 90.</p>
          </dd>
      </dl>

    ...
    </div>
    """
    rule_info = {}
    paragraphs = page_content.xpath('//div[@id="main-content"]/descendant::p')

    for paragraph in paragraphs:
        text = paragraph.text_content()
        if ": " not in text:
            continue

        parts = text.split(": ")
        if len(parts) > 2:
            continue

        if parts[0] in ["Identifier", "Trigger type", "AWS Region", "Resource Types"]:
            rule_info[parts[0]] = parts[1]

    # The parameters are in their own "div", so handle them separately.
    rule_info["Parameters"] = extract_param_info(page_content)
    return rule_info


def process_cmdline_args():
    """Return parsed command line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Scrape web pages with AWS config rules and merge results to "
            f"create the JSON file {MANAGED_RULES_OUTPUT_FILENAME}"
        )
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Report on progress"
    )
    return parser.parse_args()


def main():
    """Create a JSON file containing info pulled from AWS online docs."""
    args = process_cmdline_args()

    # Get the list of links for all the services.
    page = requests.get(AWS_CONFIG_MANAGED_RULES_URL_START + LIST_OF_RULES_URL)
    tree = html.fromstring(page.content)
    links = [x.lstrip("./") for x in tree.xpath('//div[@class="highlights"]//ul//a/@href')]

    # From each linked page, extract the id, region, trigger type and parameter
    # information.
    managed_rules = {"ManagedRules": {}}
    for link in links:
        if args.verbose:
            print(f"Extracting from {link} ...")
        page = requests.get(AWS_CONFIG_MANAGED_RULES_URL_START + link)
        rules = extract_managed_rule_info(html.fromstring(page.content))

        rule_id = rules.pop("Identifier")
        managed_rules["ManagedRules"][rule_id] = rules

    # Create a JSON file with the extracted managed rule info.
    with open(MANAGED_RULES_OUTPUT_FILENAME, "w", encoding="utf-8") as fhandle:
        json.dump(managed_rules, fhandle, sort_keys=True, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
