#!/usr/bin/env python
# -*- coding: utf-8 -*-

import boto3
import json
import os
import subprocess
from time import sleep

PATH = "moto/rds/resources/option_group_options"


def main():
    print("Getting Option Group Options from RDS Engines")
    engines = [
        "db2-ae",
        "db2-se",
        "mariadb",
        "mysql",
        "oracle-ee",
        "oracle-ee-cdb",
        "oracle-se2",
        "oracle-se2-cdb",
        "postgres",
        "sqlserver-ee",
        "sqlserver-se",
        "sqlserver-ex",
        "sqlserver-web",
    ]
    root_dir = (
        subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
        .decode()
        .strip()
    )
    rds = boto3.client("rds", region_name="us-east-1")
    for engine in engines:
        print(f"Engine {engine}...")
        dest = os.path.join(root_dir, "{0}/{1}.json".format(PATH, engine))
        try:
            option_group_options = []
            paginator = rds.get_paginator('describe_option_group_options')
            pages = paginator.paginate(EngineName=engine)
            for page in pages:
                option_group_options.extend(page["OptionGroupOptions"])
            print("Writing data to {0}".format(dest))
            with open(dest, "w+") as open_file:
                json.dump(option_group_options, open_file, indent=1, separators=(",", ":"))
        except Exception as e:
            print("Unable to write data to {0}".format(dest))
            print(e)
        # We don't want it to look like we're DDOS'ing AWS
        sleep(1)


if __name__ == "__main__":
    main()
