#!/usr/bin/env python
import json
import os
import subprocess
import requests
from bs4 import BeautifulSoup
import numpy as np

def write_file(result):
    root_dir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
    dest = os.path.join(root_dir, 'moto/ec2/resources/instance_types_hash.csv')
    print("Writing data to {0}".format(dest))
    np.savetxt("output.csv", result, delimiter=",", fmt="%s")

def parse_html(url):

    # print("Getting HTML from " + url)
    page_request = requests.get(url)
    soup = BeautifulSoup(page_request.text, 'html.parser')

    # main table with all the instance types
    main_table = soup.find("table")

    # main tbody with the instance types
    tbody = main_table.tbody

    # each tr is its own instance type
    soup_instance_types = tbody.find_all("tr")

    return soup_instance_types


def build_numpy_array(soup_instance_types):

    number_of_instance_types = len(list(soup_instance_types))

    instance_types = np.zeros(number_of_instance_types, dtype="U20")

    for i in np.arange(0, number_of_instance_types):
        instance_types[i] = soup_instance_types[i]["id"]

    np.sort(instance_types, kind="mergesort")

    return instance_types

def hash_function(instance_family):
    sum = 0

    char_array = list(instance_family)
    family_length = np.size(char_array)

    for i in range(0, family_length):
        sum += ord(char_array[i])

    return sum % 17


def build_hash(instance_types, column_length):

    # builds a hash table of the instances based on the instance family for quicker searching
    hash_instances = np.zeros((17,column_length), dtype="U20")
    # used to keep track of how many instances are in each row of table
    rows_count = np.zeros(17, dtype=np.int)

    for i in np.arange(0, np.size(instance_types)):
        family_split = instance_types[i].split(".")
        j = hash_function(family_split[0])
        hash_instances[j][rows_count[j]] = instance_types[i]
        rows_count[j] += 1

    return hash_instances



def main():

    soup_instance_types = parse_html("http://www.ec2instances.info")

    instance_types = build_numpy_array(soup_instance_types)

    # column length is currently 15
    # but if a bunch new instances types get added, it may need to be increased
    column_length = 15

    hash_instances = build_hash(instance_types, column_length)

    write_file(hash_instances)


if __name__ == '__main__':
    main()
