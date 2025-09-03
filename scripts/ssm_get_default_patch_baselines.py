import json
import re
from pathlib import Path

import boto3

session = boto3.Session(profile_name="SandboxPowerUsers")

def save_to_file(destination_path: str, content: dict):
    print("Attempting to save data to {}", destination_path)
    file_path = Path(Path.cwd(), destination_path)
    file_path.parent.mkdir(exist_ok=True, parents=True)

    with file_path.open("w", encoding="utf-8") as fb:
        json.dump(content, fb, sort_keys=True, indent=2)


def get_region_baselines(client, operating_systems: list[str]) -> dict[str, str]:
    print(
        "Retrieving default patch baselines per region. "
        "AWS has a different account id per region that is used to store the  patch baselines.\n\n"
    )
    regex = r"AWS-[a-zA-Z0-9_]*DefaultPatchBaseline"
    region_dict = dict.fromkeys(operating_systems)

    paginator = client.get_paginator("describe_patch_baselines")
    response_iterator = paginator.paginate(
        Filters=[
            {
                "Key": "OWNER",
                "Values": [
                    "AWS",
                ],
            },
        ]
    )
    for response in response_iterator:
        for baseline in response["BaselineIdentities"]:
            match = re.search(regex, baseline["BaselineName"])
            if match is not None:
                region_dict[baseline["OperatingSystem"]] = baseline["BaselineId"]

    return region_dict


def main():
    """
    Retrieve default patch baselines from SSM
     - Setup search criteria for OS default baselines
     - Organize patch baselines by os and region
     - Store this in the dedicated moto/ssm/resources-folder
    """
    regions = session.get_available_regions("ssm")
    regions = ["us-west-2", "us-west-1", "us-east-1"]
    operating_systems = [
        "WINDOWS",
        "AMAZON_LINUX",
        "AMAZON_LINUX_2",
        "AMAZON_LINUX_2022",
        "UBUNTU",
        "REDHAT_ENTERPRISE_LINUX",
        "SUSE",
        "CENTOS",
        "ORACLE_LINUX",
        "DEBIAN",
        "MACOS",
        "RASPBIAN",
        "ROCKY_LINUX",
        "ALMA_LINUX",
        "AMAZON_LINUX_2023",
    ]
    master_dict = dict.fromkeys(regions)
    for region in regions:
        client = session.client("ssm", region_name=region)

        region_dict = get_region_baselines(client, operating_systems)

        master_dict[region] = region_dict

    save_to_file("moto/ssm/resources/default_baselines.json", master_dict)


if __name__ == "__main__":
    main()
