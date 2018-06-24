#!/usr/bin/env python
import json
import os
import subprocess
import requests
from bs4 import BeautifulSoup
import numpy as np


def main():
    print("Getting HTML from http://www.ec2instances.info")
    page_request = requests.get('http://www.ec2instances.info')
    soup = BeautifulSoup(page_request.text, 'html.parser')

    # main tbody with all the instance types
    main_table = soup.find("table")

    tbody = main_table.tbody

    A = tbody.find_all("tr")

    for i in np.arange(0, len(list(A))):
        print(A[i]["id"])

if __name__ == '__main__':
    main()
