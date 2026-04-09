import boto3
import json
import time
import os
import subprocess

root_dir = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()


def list_release_labels(client) -> list[str]:
    x = client.list_release_labels()
    release_labels = x["ReleaseLabels"]
    next_token = x.get("NextToken")
    while next_token:
        x = client.list_release_labels(NextToken=next_token)
        release_labels.extend(x["ReleaseLabels"])
        next_token = x.get("NextToken")

    return release_labels


def list_supported_instance_types(client, release_label: str):
    x = client.list_supported_instance_types(ReleaseLabel=release_label)
    instance_types = x["SupportedInstanceTypes"]
    next_token = x.get("Marker")
    while next_token:
        x = client.list_supported_instance_types(ReleaseLabel=release_label, Marker=next_token)
        instance_types.extend(x["SupportedInstanceTypes"])
        next_token = x.get("Marker")

    return instance_types


def download_release_label(region, release_label):
    client = boto3.client("emr", region_name=region)

    instance_types = list_supported_instance_types(client, release_label=release_label)

    dest = os.path.join(
        root_dir, f"moto/emr/resources/instance-types-{release_label}.json"
    )
    print("Writing data to {0}".format(dest))
    with open(dest, "w") as open_file:
        json.dump(instance_types, open_file, sort_keys=True, indent=2)

    time.sleep(0.1)


def list_instance_types(release_label):
    client = boto3.client("emr", region_name="us-east-1")

    try:
        return list_supported_instance_types(client, release_label=release_label)
    except:
        try:
            client2 = boto3.client("emr", region_name="us-east-2")
            return list_supported_instance_types(client2, release_label=release_label)
        except Exception as e:
            print(f"Couldn't find release types for release_label={release_label} in region=us-east-2")
        return []


def main():
    """
    Retrieve the latest ReleaseLabels from EMR
    List the supported instance types per release label

     - Download from AWS
     - Store this in the dedicated moto/emr/resources-folder
    """

    regions = boto3.Session().get_available_regions("emr")

    all_release_labels: set[str] = set()

    for region in regions:
        client = boto3.client("emr", region_name=region)

        # Retrieve release labels for this region
        try:
            release_labels = list_release_labels(client)
            all_release_labels.update(release_labels)

            dest = os.path.join(
                root_dir, f"moto/emr/resources/release-labels-{region}.json"
            )
            print("Writing data to {0}".format(dest))
            with open(dest, "w") as open_file:
                json.dump(release_labels, open_file, sort_keys=True, indent=2)

            time.sleep(0.1)
        except Exception as e:
            print(e)
            # We might encounter an error if we do not have access to a region - just ignore and try the next region


    # Determine instance type per release label
    # Because multiple release labels use the same instance types, they are stored separately
    #
    # - instance_types.json - stores all instance types by TypeName (i.e. 'c1.medium')
    # - instance-types-emr-6.1.0 - stores the TypeNames of all instance types that can be used for Release Label EMR 6.1.0
    instance_types = {}
    for release_label in all_release_labels:
        types_per_release = list_instance_types(release_label)
        for instance_type in types_per_release:
            if instance_type["Type"] not in instance_types:
                instance_types[instance_type["Type"]] = instance_type

        dest = os.path.join(
            root_dir, f"moto/emr/resources/instance-types-{release_label}.json"
        )
        print("Writing data to {0}".format(dest))
        types = [instance_type["Type"] for instance_type in types_per_release]
        with open(dest, "w") as open_file:
            json.dump(types, open_file, sort_keys=True, indent=2)

    dest = os.path.join(
        root_dir, f"moto/emr/resources/instance_types.json"
    )
    print("Writing data to {0}".format(dest))
    with open(dest, "w") as open_file:
        json.dump(instance_types, open_file, sort_keys=True, indent=2)


if __name__ == "__main__":
    main()
