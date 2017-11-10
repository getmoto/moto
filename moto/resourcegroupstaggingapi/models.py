from __future__ import unicode_literals
import uuid
import boto3
import six
from moto.core import BaseBackend
from moto.core.exceptions import RESTError

from moto.s3 import s3_backends
from moto.ec2 import ec2_backends

# Left: EC2 ElastiCache RDS ELB CloudFront WorkSpaces Lambda EMR Glacier Kinesis Redshift Route53
# StorageGateway DynamoDB MachineLearning ACM DirectConnect DirectoryService CloudHSM
# Inspector Elasticsearch


class ResourceGroupsTaggingAPIBackend(BaseBackend):
    def __init__(self, region_name=None):
        super(ResourceGroupsTaggingAPIBackend, self).__init__()
        self.region_name = region_name

        self._pages = {}
        # Like 'someuuid': {'gen': <generator>, 'misc': None}
        # Misc is there for peeking from a generator and it cant
        # fit in the current request. As we only store generators
        # theres not really any point to clean up

    def reset(self):
        region_name = self.region_name
        self.__dict__ = {}
        self.__init__(region_name)

    @property
    def s3_backend(self):
        """
        :rtype: moto.s3.models.S3Backend
        """
        return s3_backends['global']

    @property
    def ec2_backend(self):
        """
        :rtype: moto.ec2.models.EC2Backend
        """
        return ec2_backends[self.region_name]

    def _get_resources_generator(self, tag_filters=None, resource_type_filters=None):
        # TODO move these to their respective backends

        # Do S3
        for bucket in self.s3_backend.buckets.values():
            tags = []
            for tag in bucket.tags.tag_set.tags:
                tags.append({'Key': tag.key, 'Value': tag.value})

            yield {'ResourceARN': 'arn:aws:s3:::' + bucket.name, 'Tags': tags}

        # EC2 tags
        def get_ec2_tags(res_id):
            result = []
            for key, value in self.ec2_backend.tags.get(res_id, {}).items():
                result.append({'Key': key, 'Value': value})
            return result

        # EC2 AMI
        for ami in self.ec2_backend.amis.values():
            yield {'ResourceARN': 'arn:aws:ec2:{0}::image/{1}'.format(self.region_name, ami.id), 'Tags': get_ec2_tags(ami.id)}

        # EC2 Instance
        for reservation in self.ec2_backend.reservations.values():
            for instance in reservation.instances:
                yield {'ResourceARN': 'arn:aws:ec2:{0}::instance/{1}'.format(self.region_name, instance.id), 'Tags': get_ec2_tags(instance.id)}
        # EC2 NetworkInterface
        for eni in self.ec2_backend.enis.values():
            yield {'ResourceARN': 'arn:aws:ec2:{0}::network-interface/{1}'.format(self.region_name, eni.id), 'Tags': get_ec2_tags(eni.id)}
        # TODO EC2 ReservedInstance
        # EC2 SecurityGroup
        for vpc in self.ec2_backend.groups.values():
            for sg in vpc.values():
                yield {'ResourceARN': 'arn:aws:ec2:{0}::security-group/{1}'.format(self.region_name, sg.id), 'Tags': get_ec2_tags(sg.id)}
        # EC2 Snapshot
        for snapshot in self.ec2_backend.snapshots.values():
            yield {'ResourceARN': 'arn:aws:ec2:{0}::snapshot/{1}'.format(self.region_name, snapshot.id), 'Tags': get_ec2_tags(snapshot.id)}
        # TODO EC2 SpotInstanceRequest
        # EC2 Volume
        for volume in self.ec2_backend.volumes.values():
            yield {'ResourceARN': 'arn:aws:ec2:{0}::volume/{1}'.format(self.region_name, volume.id), 'Tags': get_ec2_tags(volume.id)}

        # ELB

        # EMR Cluster

        # Glacier Vault

        # Kinesis

        # RDS Instance
        # RDS Reserved Database Instance
        # RDS Option Group
        # RDS Parameter Group
        # RDS Security Group
        # RDS Snapshot
        # RDS Subnet Group
        # RDS Event Subscription

        # RedShift Cluster
        # RedShift Hardware security module (HSM) client certificate
        # RedShift HSM connection
        # RedShift Parameter group
        # RedShift Snapshot
        # RedShift Subnet group

        # VPC
        # VPC Customer Gateway
        # VPC DHCP Option Set
        # VPC Internet Gateway
        # VPC Network ACL
        # VPC Route Table
        # VPC Subnet
        # VPC Virtual Private Gateway
        # VPC VPN Connection

    def get_resources(self, pagination_token=None,
                      resources_per_page=50, tags_per_page=100,
                      tag_filters=None, resource_type_filters=None):
        # Simple range checning
        if 100 >= tags_per_page >= 500:
            raise RESTError('InvalidParameterException', 'TagsPerPage must be between 100 and 500')
        if 1 >= resources_per_page >= 50:
            raise RESTError('InvalidParameterException', 'ResourcesPerPage must be between 100 and 500')

        # If we have a token, go and find the respective generator, or error
        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError('PaginationTokenExpiredException', 'Token does not exist')

            generator = self._pages[pagination_token]['gen']
            left_over = self._pages[pagination_token]['misc']
        else:
            generator = self._get_resources_generator(tag_filters=tag_filters,
                                                      resource_type_filters=resource_type_filters)
            left_over = None

        result = []
        current_tags = 0
        current_resources = 0
        if left_over:
            result.append(left_over)
            current_resources += 1
            current_tags += len(left_over['Tags'])

        try:
            while True:
                # Generator format: [{'ResourceARN': str, 'Tags': [{'Key': str, 'Value': str]}, ...]
                next_item = six.next(generator)
                resource_tags = len(next_item['Tags'])

                if current_resources >= resources_per_page:
                    break
                if current_tags + resource_tags >= tags_per_page:
                    break

                current_resources += 1
                current_tags += resource_tags

                result.append(next_item)

        except StopIteration:
            # Finished generator before invalidating page limiting constraints
            return None, result

        # Didn't hit StopIteration so there's stuff left in generator
        new_token = str(uuid.uuid4())
        self._pages[new_token] = {'gen': generator, 'misc': next_item}

        # Token used up, might as well bin now, if you call it again your an idiot
        if pagination_token:
            del self._pages[pagination_token]

        return new_token, result

    # def get_tag_keys(self, pagination_token):
    #     return pagination_token, tag_keys
    #
    # def get_tag_values(self, pagination_token, key):
    #     return pagination_token, tag_values
    #
    # def tag_resources(self, resource_arn_list, tags):
    #     return failed_resources_map
    #
    # def untag_resources(self, resource_arn_list, tag_keys):
    #     return failed_resources_map


available_regions = boto3.session.Session().get_available_regions("resourcegroupstaggingapi")
resourcegroupstaggingapi_backends = {region: ResourceGroupsTaggingAPIBackend(region) for region in available_regions}
