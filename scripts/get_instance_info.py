#!/usr/bin/env python
import json
import os
import subprocess
import requests
from bs4 import BeautifulSoup


class Instance(object):
    def __init__(self, instance):
        self.instance = instance

    def _get_td(self, td):
        return self.instance.find('td', attrs={'class': td})

    def _get_sort(self, td):
        return float(self.instance.find('td', attrs={'class': td}).find('span')['sort'])

    @property
    def name(self):
        return self._get_td('name').text.strip()

    @property
    def apiname(self):
        return self._get_td('apiname').text.strip()

    @property
    def memory(self):
        return self._get_sort('memory')

    @property
    def computeunits(self):
        return self._get_sort('computeunits')

    @property
    def vcpus(self):
        return self._get_sort('vcpus')

    @property
    def gpus(self):
        return int(self._get_td('gpus').text.strip())

    @property
    def fpga(self):
        return int(self._get_td('fpga').text.strip())

    @property
    def ecu_per_vcpu(self):
        return self._get_sort('ecu-per-vcpu')

    @property
    def physical_processor(self):
        return self._get_td('physical_processor').text.strip()

    @property
    def clock_speed_ghz(self):
        return self._get_td('clock_speed_ghz').text.strip()

    @property
    def intel_avx(self):
        return self._get_td('intel_avx').text.strip()

    @property
    def intel_avx2(self):
        return self._get_td('intel_avx2').text.strip()

    @property
    def intel_turbo(self):
        return self._get_td('intel_turbo').text.strip()

    @property
    def storage(self):
        return self._get_sort('storage')

    @property
    def architecture(self):
        return self._get_td('architecture').text.strip()

    @property
    def network_perf(self):  # 2 == low
        return self._get_sort('networkperf')

    @property
    def ebs_max_bandwidth(self):
        return self._get_sort('ebs-max-bandwidth')

    @property
    def ebs_throughput(self):
        return self._get_sort('ebs-throughput')

    @property
    def ebs_iops(self):
        return self._get_sort('ebs-iops')

    @property
    def max_ips(self):
        return int(self._get_td('maxips').text.strip())

    @property
    def enhanced_networking(self):
        return self._get_td('enhanced-networking').text.strip() != 'No'

    @property
    def vpc_only(self):
        return self._get_td('vpc-only').text.strip() != 'No'

    @property
    def ipv6_support(self):
        return self._get_td('ipv6-support').text.strip() != 'No'

    @property
    def placement_group_support(self):
        return self._get_td('placement-group-support').text.strip() != 'No'

    @property
    def linux_virtualization(self):
        return self._get_td('linux-virtualization').text.strip()

    def to_dict(self):
        result = {}

        for attr in [x for x in self.__class__.__dict__.keys() if not x.startswith('_') and x != 'to_dict']:
            result[attr] = getattr(self, attr)

        return self.apiname, result


def main():
    print("Getting HTML from http://www.ec2instances.info")
    page_request = requests.get('http://www.ec2instances.info')
    soup = BeautifulSoup(page_request.text, 'html.parser')
    data_table = soup.find(id='data')

    print("Finding data in table")
    instances = data_table.find('tbody').find_all('tr')

    print("Parsing data")
    result = {}
    for instance in instances:
        instance_id, instance_data = Instance(instance).to_dict()
        result[instance_id] = instance_data

    root_dir = subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip()
    dest = os.path.join(root_dir, 'moto/ec2/resources/instance_types.json')
    print("Writing data to {0}".format(dest))
    with open(dest, 'w') as open_file:
        json.dump(result, open_file)

if __name__ == '__main__':
    main()
