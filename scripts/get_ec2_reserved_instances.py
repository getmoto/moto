import boto3
import numpy as np
from time import sleep
import subprocess
import os
import botocore
from random import randint


hash_table_size = 2011 # prime number and size of hash table
hash_table_divider = 10 # number of files to divide
hash_table_bin = int(np.ceil(hash_table_size/hash_table_divider)) # number of lines in each file rounded up (21)

def get_file_name(region, instance_type):

    return region.replace("-", "_") + "_" + instance_type.replace(".", "_")


def get_index_of_hash_tables(index):
    """
    Index of the line if the hash table was one giant file.
    """
    index_file = int(np.floor(index/hash_table_bin))

    return index_file

def get_index_hash_adjusted(index_file, index):
    """
    Index with the main hash table broken up into 100 parts.
    """

    index_adjusted = (index % hash_table_bin)

    return index_adjusted

def save_hash_table(Region_Hash_list, regions):

    root_dir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']
                                       ).decode().strip()

    for r in np.arange(0, len(Region_Hash_list)):
        for i in np.arange(0, len(Region_Hash_list[r])):
            file_name = "offering_ids_hash_" + str(i) + ".csv"
            region = regions[r]
            folder_name = regions[r].replace("-", "_")

            dest = os.path.join(root_dir, "moto/ec2/resources/reserved_instances/" + folder_name + "/"
                                + file_name)

            np.savetxt(dest, Region_Hash_list[r][i], fmt="%s", delimiter=",", newline="\n")


def save_reserved_instance_offerings(RI_Table, region, instance_type):
    header_list = list(RI_Table.dtype.fields)
    header = ""
    for i in np.arange(0, len(header_list)):
        if i < len(header_list) - 1:
            header = header + header_list[i] + ","
        else:
            header = header + header_list[i]

    root_dir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']
                                       ).decode().strip()

    file_name = get_file_name(region, instance_type) + ".csv"

    dest = os.path.join(root_dir, 'moto/ec2/resources/reserved_instances/' + region.replace("-", "_") + "/" + file_name)

    np.savetxt(dest,RI_Table, fmt="%s", delimiter=",", newline="\n", header=header, comments="")


def parse_individual_reserved_instance(ri_table, ri):
    ri_table[0] = ri["ReservedInstancesOfferingId"]
    ri_table[1] = ri["InstanceType"]
    ri_table[2] = ri["ProductDescription"]
    ri_table[3] = ri["InstanceTenancy"]
    ri_table[4] = ri["OfferingClass"]
    ri_table[5] = ri["OfferingType"]
    if ri["Scope"] == "Availability Zone":
        ri_table[8] = "Availability Zone"
        ri_table[6] = ri["AvailabilityZone"]
    else:
        ri_table[8] = ri["Scope"]
    ri_table[7] = ri["Duration"]
    # only supports non-marketplace offerings currently so hard-coded as False (0)
    ri_table[9] = "0"
    ri_table[10] = ri["FixedPrice"]
    ri_table[11] = ri["UsagePrice"]
    ri_table[12] = ri["CurrencyCode"]
    if len(ri["RecurringCharges"]) > 0:
        # some offerings have recurring charges and some (but not all)
        # All Upfront RI's have an empty list
        ri_table[13] = ri["RecurringCharges"][0]["Amount"]
        ri_table[14] = ri["RecurringCharges"][0]["Frequency"]
    else:
        ri_table[13] = 0.0
        ri_table[14] = "Hourly"

def hash_function(offering_id_head):
    sum = 0

    char_array = np.array(list(offering_id_head))
    normalized = char_array.view(np.uint32)
    sum = int(np.sum(normalized))

    return sum % hash_table_size

def polyhash_prime(offering_id, a, p, m):
    # hash function from https://startupnextdoor.com/spending-a-couple-days-on-hashing-functions/
    hash = 0

    for c in offering_id:
        hash = (hash*a + ord(c)) % p

    return np.abs(hash % m)


def add_to_hash_table(ri, region, Region_Hash_list, Hash_Table_Count, r):
    offering_id = ri["ReservedInstancesOfferingId"]
    instance_type = ri["InstanceType"]

    file_name = get_file_name(region, instance_type)
    ref_value = offering_id[0:8] + "|" + file_name

    index = polyhash_prime(offering_id[0:8], 31, 12011, hash_table_size)

    index_file = get_index_of_hash_tables(index)

    index_adjusted = get_index_hash_adjusted(index_file, index)

    Hash_Table_Count[r, index] += 1

    # used to find the next available empty space in hash table
    check = np.where(Region_Hash_list[r][index_file][index_adjusted] == "0")[0]
    if np.size(check) > 0:
        j = check[0]
        Region_Hash_list[r][index_file][index_adjusted][j] = ref_value
    else:
        print("Hash Table " + str(r) + " (" + str(region) + ") has run rut of space")


def parse_reserved_instance_offerings(ri_offerings, region, Region_Hash_list,
                                      Hash_Table_Count, r):

    offerings_count = np.size(ri_offerings)

    if offerings_count < 1:
        return None

    ri_table_dtype = [("ReservedInstancesOfferings", "U36"),
                      ("InstanceType", "U20"),
                      ("ProductDescription", "U36"),
                      ("InstanceTenancy", "U9"),
                      ("OfferingClass", "U11"),
                      ("OfferingType", "U15"),
                      ("AvailabilityZone", "U20"),
                      ("Duration", "i4"),
                      ("Scope", "U18"),
                      ("Marketplace", "U1"),
                      ("FixedPrice", "f4"),
                      ("UsagePrice", "f4"),
                      ("CurrencyCode", "U3"),
                      ("Amount", "f4"),
                      ("Frequency", "U6")]

    ri_table_partial = np.zeros(offerings_count, dtype=ri_table_dtype)
    for i in np.arange(0, offerings_count):
        parse_individual_reserved_instance(ri_table_partial[i], ri_offerings[i])
        add_to_hash_table(ri_offerings[i], region, Region_Hash_list, Hash_Table_Count, r)

    return ri_table_partial


def get_offerings_check_rate_limit(client,instance_type, NextToken, RI_Table, region, Region_Hash_list, Hash_Table_Count, r):
    try:
        return get_offerings(client,instance_type, NextToken, RI_Table, region, Region_Hash_list, Hash_Table_Count, r)
    except botocore.exceptions.ClientError as e:
        timeout = 60
        print("[Warning] API rate exceeded, throttling back for 60 seconds")
        sleep(timeout)

        return get_offerings(client,instance_type, NextToken, RI_Table, region, Region_Hash_list, Hash_Table_Count, r)


def get_offerings(client,instance_type, NextToken, RI_Table, region, Region_Hash_list, Hash_Table_Count, r):
    offerings = 0
    # print(RI_Table)

    if NextToken == "start":
        # first step in, no token givern
        offerings = client.describe_reserved_instances_offerings(
                InstanceType=instance_type, IncludeMarketplace=False, MaxResults=100)

        if "ReservedInstancesOfferings" in offerings:
            temp_table = parse_reserved_instance_offerings(
                            offerings["ReservedInstancesOfferings"],
                            region, Region_Hash_list, Hash_Table_Count, r)
        else:
            return RI_Table, "end"

        if temp_table is not None:
            RI_Table = temp_table
            if "NextToken" in offerings:
                NextToken = offerings["NextToken"]
                return RI_Table, NextToken
            else:
                return RI_Table, "end"
        else:
            return RI_Table, "end"

    else:
        # deeper steps
        offerings = client.describe_reserved_instances_offerings(
                InstanceType=instance_type, IncludeMarketplace=False, MaxResults=100, NextToken=NextToken)

        if "ReservedInstancesOfferings" in offerings:
            temp_table = parse_reserved_instance_offerings(
                            offerings["ReservedInstancesOfferings"],
                            region, Region_Hash_list, Hash_Table_Count, r)
        else:
            return RI_Table, "end"

        if temp_table is not None:
            # combines two tables, need to check if this works as intended
            RI_Table = np.append(RI_Table, temp_table)
            if "NextToken" in offerings:
                NextToken = offerings["NextToken"]
                return RI_Table, NextToken
            else:
                return RI_Table, "end"
        else:
            return RI_Table, "end"


def get_regions(session):

    client = session.client("ec2", region_name="us-east-1")

    regions_output = client.describe_regions()["Regions"]

    regions = []
    for i in np.arange(0,np.size(regions_output)):
        regions.append(regions_output[i]["RegionName"])

    return regions
    # return ["ap-south-1", "us-east-1"]
    # return ["ap-south-1"]

def get_instance_types(session):

    client = session.client("ec2", region_name="us-east-1")

    offerings_per_instance_type = client.describe_reserved_instances_offerings(
        InstanceTenancy="default",
        AvailabilityZone="us-east-1b", OfferingType="No Upfront",
        OfferingClass="standard", MinDuration=31536000, MaxDuration=31536000,
        IncludeMarketplace=False,
        ProductDescription="Linux/UNIX")["ReservedInstancesOfferings"]

    instance_types = []
    for i in np.arange(0, np.size(offerings_per_instance_type)):
        instance_types.append(offerings_per_instance_type[i]["InstanceType"])

    return instance_types
    # return ["t2.nano", "m5.large", "r4.xlarge", "c5d.large"]
    # return ["c5d.large"]


def build_ec2_reserved_instances(session, regions, instance_types):

    Region_Hash_list = []

    for k in np.arange(0, np.size(regions)):
        Hash_Tables = []
        for i in np.arange(0, hash_table_divider):
            Hash_Tables.append(np.full((hash_table_bin, 90), "0", dtype="U35", order="C"))
        Region_Hash_list.append(Hash_Tables)

    Hash_Table_Count = np.zeros((np.size(regions), hash_table_size), dtype=np.int64)

    RI_Table = None
    r = 0 # used to keep track of regions
    for region in regions:
        print("")
        print(region)
        for instance_type in instance_types:
            print(instance_type)
            RI_Table = None # resets RI_Table if a region has no RI's for that instance type
            client = session.client("ec2", region_name=region)
            NextToken = "start"

            while True == True:
                RI_Table, NextToken = get_offerings_check_rate_limit(client,instance_type, NextToken, RI_Table, region, Region_Hash_list, Hash_Table_Count, r)
                if NextToken == "end":
                    break
            if RI_Table is not None:
                save_reserved_instance_offerings(RI_Table, region, instance_type)
            else:
                print("No RIs for " + region + " " + instance_type)
        r += 1
    save_hash_table(Region_Hash_list, regions)
    print("Max Bin in Hash Table: " + str(np.max(Hash_Table_Count)))
    np.savetxt("Hash_Table_Count.csv", Hash_Table_Count, fmt="%s")



def main():
    session = boto3.Session(profile_name="moto_role_builder")

    regions = get_regions(session)

    instance_types = get_instance_types(session)

    build_ec2_reserved_instances(session, regions, instance_types)


if __name__ == "__main__":
    main()
