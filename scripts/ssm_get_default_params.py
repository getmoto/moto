import boto3
import json
import os
import subprocess
import time

import moto
from moto.utilities.utils import load_resource
from moto.ssm.utils import convert_to_tree


root_dir = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()


alt_names = {
    "lambda": "awslambda",
    "aps": "amp",  # Prometheus
    "costexplorer": "ce",
    "waf": "wafv2",
    "identitystore": "ssoadmin"
}


def retrieve_by_path(client, path):
    print(f"Retrieving all parameters from {path}. "
          f"AWS has around 14000 parameters, and we can only retrieve 10 at the time, so this may take a while.\n\n")
    x = client.get_parameters_by_path(Path=path, Recursive=True)
    parameters = x["Parameters"]
    next_token = x["NextToken"]
    while next_token:
        x = client.get_parameters_by_path(Path=path, Recursive=True, NextToken=next_token)
        parameters.extend(x["Parameters"])
        next_token = x.get("NextToken")
        if len(parameters) % 100 == 0:
            print(f"Retrieved {len(parameters)} from {path}...")
            time.sleep(0.5)

    return parameters


def main():
    """
    Retrieve global parameters from SSM
     - Download from AWS
     - Convert them to a more space-optimized data format
     - Store this in the dedicated moto/ssm/resources-folder

     Note:
         There are around 20k parameters, and we can only retrieve 10 at a time.
         So running this scripts takes a while.
    """

    client = boto3.client('ssm', region_name="us-west-1")

    default_param_paths = ["/aws/service/global-infrastructure/regions",
                           "/aws/service/global-infrastructure/services"]

    for path in default_param_paths:
        params = retrieve_by_path(client, path)
        tree = convert_to_tree(params)

        filename = "{}.json".format(path.split("/")[-1])
        dest = os.path.join(root_dir, "moto/ssm/resources/{}".format(filename))
        print("Writing data to {0}".format(dest))
        with open(dest, "w") as open_file:
            json.dump(tree, open_file, sort_keys=True, indent=2)

    services = load_resource(moto.__name__, "ssm/resources/services.json")["aws"]["service"]["global-infrastructure"]["services"]
    all_regions = set()
    for service in services.keys():
        all_regions.update(list(services[service].get("regions", {}).keys()))

    regions_by_service = {"__all": list(all_regions)}
    for service in services.keys():
        regions = set(services[service].get("regions", {}).keys())
        if regions != set(regions_by_service["__all"]):
            clean_name = alt_names.get(service, service).replace("-", "")
            if f"mock_{clean_name}" in dir(moto):
                regions_by_service[service] = sorted(regions)

    dest = os.path.join(root_dir, "moto/core/regions.json")
    print("Writing data to {0}".format(dest))
    with open(dest, "w") as open_file:
        # Yes, json.dump exists
        # But this gives us more control over the indentation options
        open_file.write("{\n")
        for idx, key in enumerate(sorted(regions_by_service.keys())):
            open_file.write(f"  \"{key}\": [")
            open_file.write(", ".join([f"\"{s}\"" for s in sorted(regions_by_service[key])]))
            open_file.write("]\n" if (idx == len(regions_by_service.keys())-1) else "],\n")
        open_file.write("}")


if __name__ == "__main__":
    main()
