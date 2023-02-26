#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import json
import os
import subprocess
from moto.rds.utils import encode_orderable_db_instance
from time import sleep

PATH = "moto/rds/resources/cluster_options"


def main():
    print("Getting DB Cluster Options from just neptune for now")
    engines = ["neptune"]

    root_dir = (
        subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
        .decode()
        .strip()
    )
    rds = boto3.client("rds", region_name="us-east-1")
    for engine in engines:
        print(f"Engine {engine}...")
        dest = os.path.join(
            root_dir, "{0}/{1}.json".format(PATH, engine)
        )
        try:
            options = []
            response = rds.describe_orderable_db_instance_options(Engine=engine)
            options.extend(response["OrderableDBInstanceOptions"])
            next_token = response.get("Marker", None)
            while next_token:
                response = rds.describe_orderable_db_instance_options(
                    Engine=engine, Marker=next_token
                )
                options.extend(response["OrderableDBInstanceOptions"])
                next_token = response.get("Marker", None)

            options = [encode_orderable_db_instance(option) for option in options]
            print("Writing data to {0}".format(dest))
            with open(dest, "w+") as open_file:
                json.dump(options, open_file, indent=1, separators=(",", ":"))
        except Exception as e:
            print("Unable to write data to {0}".format(dest))
            print(e)
        # We don't want it to look like we're DDOS'ing AWS
        sleep(1)


if __name__ == "__main__":
    main()
