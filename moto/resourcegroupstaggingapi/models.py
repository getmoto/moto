from __future__ import unicode_literals
import uuid
import boto3
import six
from moto.core import BaseBackend
from moto.core.exceptions import RESTError

from moto.s3 import s3_backends
from moto.ec2 import ec2_backends
from moto.elb import elb_backends
from moto.elbv2 import elbv2_backends
from moto.kinesis import kinesis_backends
from moto.rds2 import rds2_backends
from moto.glacier import glacier_backends
from moto.redshift import redshift_backends
from moto.emr import emr_backends

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

    @property
    def elb_backend(self):
        """
        :rtype: moto.elb.models.ELBBackend
        """
        return elb_backends[self.region_name]

    @property
    def elbv2_backend(self):
        """
        :rtype: moto.elbv2.models.ELBv2Backend
        """
        return elbv2_backends[self.region_name]

    @property
    def kinesis_backend(self):
        """
        :rtype: moto.kinesis.models.KinesisBackend
        """
        return kinesis_backends[self.region_name]

    @property
    def rds_backend(self):
        """
        :rtype: moto.rds2.models.RDS2Backend
        """
        return rds2_backends[self.region_name]

    @property
    def glacier_backend(self):
        """
        :rtype: moto.glacier.models.GlacierBackend
        """
        return glacier_backends[self.region_name]

    @property
    def emr_backend(self):
        """
        :rtype: moto.emr.models.ElasticMapReduceBackend
        """
        return emr_backends[self.region_name]

    @property
    def redshift_backend(self):
        """
        :rtype: moto.redshift.models.RedshiftBackend
        """
        return redshift_backends[self.region_name]

    def _get_resources_generator(self, tag_filters=None, resource_type_filters=None):
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # TODO move these to their respective backends
        filters = [lambda t, v: True]
        for tag_filter_dict in tag_filters:
            values = tag_filter_dict.get('Values', [])
            if len(values) == 0:
                # Check key matches
                filters.append(lambda t, v: t == tag_filter_dict['Key'])
            elif len(values) == 1:
                # Check its exactly the same as key, value
                filters.append(lambda t, v: t == tag_filter_dict['Key'] and v == values[0])
            else:
                # Check key matches and value is one of the provided values
                filters.append(lambda t, v: t == tag_filter_dict['Key'] and v in values)

        def tag_filter(tag_list):
            result = []
            if tag_filters:
                for tag in tag_list:
                    temp_result = []
                    for f in filters:
                        f_result = f(tag['Key'], tag['Value'])
                        temp_result.append(f_result)
                    result.append(all(temp_result))

                return any(result)
            else:
                return True

        # Do S3, resource type s3
        if not resource_type_filters or 's3' in resource_type_filters:
            for bucket in self.s3_backend.buckets.values():
                tags = []
                for tag in bucket.tags.tag_set.tags:
                    tags.append({'Key': tag.key, 'Value': tag.value})

                if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue
                yield {'ResourceARN': 'arn:aws:s3:::' + bucket.name, 'Tags': tags}

        # EC2 tags
        def get_ec2_tags(res_id):
            result = []
            for key, value in self.ec2_backend.tags.get(res_id, {}).items():
                result.append({'Key': key, 'Value': value})
            return result

        # EC2 AMI, resource type ec2:image
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:image' in resource_type_filters:
            for ami in self.ec2_backend.amis.values():
                tags = get_ec2_tags(ami.id)

                if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue
                yield {'ResourceARN': 'arn:aws:ec2:{0}::image/{1}'.format(self.region_name, ami.id), 'Tags': tags}

        # EC2 Instance, resource type ec2:instance
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:instance' in resource_type_filters:
            for reservation in self.ec2_backend.reservations.values():
                for instance in reservation.instances:
                    tags = get_ec2_tags(instance.id)

                    if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                        continue
                    yield {'ResourceARN': 'arn:aws:ec2:{0}::instance/{1}'.format(self.region_name, instance.id), 'Tags': tags}

        # EC2 NetworkInterface, resource type ec2:network-interface
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:network-interface' in resource_type_filters:
            for eni in self.ec2_backend.enis.values():
                tags = get_ec2_tags(eni.id)

                if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue
                yield {'ResourceARN': 'arn:aws:ec2:{0}::network-interface/{1}'.format(self.region_name, eni.id), 'Tags': tags}

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:security-group' in resource_type_filters:
            for vpc in self.ec2_backend.groups.values():
                for sg in vpc.values():
                    tags = get_ec2_tags(sg.id)

                    if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                        continue
                    yield {'ResourceARN': 'arn:aws:ec2:{0}::security-group/{1}'.format(self.region_name, sg.id), 'Tags': tags}

        # EC2 Snapshot, resource type ec2:snapshot
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:snapshot' in resource_type_filters:
            for snapshot in self.ec2_backend.snapshots.values():
                tags = get_ec2_tags(snapshot.id)

                if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue
                yield {'ResourceARN': 'arn:aws:ec2:{0}::snapshot/{1}'.format(self.region_name, snapshot.id), 'Tags': tags}

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        if not resource_type_filters or 'ec2' in resource_type_filters or 'ec2:volume' in resource_type_filters:
            for volume in self.ec2_backend.volumes.values():
                tags = get_ec2_tags(volume.id)

                if not tags or not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue
                yield {'ResourceARN': 'arn:aws:ec2:{0}::volume/{1}'.format(self.region_name, volume.id), 'Tags': tags}

        # TODO add these to the keys and values functions / combine functions
        # ELB

        def get_elbv2_tags(arn):
            result = []
            for key, value in self.elbv2_backend.load_balancers[elb.arn].tags.items():
                result.append({'Key': key, 'Value': value})
            return result

        if not resource_type_filters or 'elasticloadbalancer' in resource_type_filters or 'elasticloadbalancer:loadbalancer' in resource_type_filters:
            for elb in self.elbv2_backend.load_balancers.values():
                tags = get_elbv2_tags(elb.arn)
                # if 'elasticloadbalancer:loadbalancer' in resource_type_filters:
                #     from IPython import embed
                #     embed()
                if not tag_filter(tags):  # Skip if no tags, or invalid filter
                    continue

                yield {'ResourceARN': '{0}'.format(elb.arn), 'Tags': tags}

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

    def _get_tag_keys_generator(self):
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Do S3, resource type s3
        for bucket in self.s3_backend.buckets.values():
            for tag in bucket.tags.tag_set.tags:
                yield tag.key

        # EC2 tags
        def get_ec2_keys(res_id):
            result = []
            for key in self.ec2_backend.tags.get(res_id, {}):
                result.append(key)
            return result

        # EC2 AMI, resource type ec2:image
        for ami in self.ec2_backend.amis.values():
            for key in get_ec2_keys(ami.id):
                yield key

        # EC2 Instance, resource type ec2:instance
        for reservation in self.ec2_backend.reservations.values():
            for instance in reservation.instances:
                for key in get_ec2_keys(instance.id):
                    yield key

        # EC2 NetworkInterface, resource type ec2:network-interface
        for eni in self.ec2_backend.enis.values():
            for key in get_ec2_keys(eni.id):
                yield key

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        for vpc in self.ec2_backend.groups.values():
            for sg in vpc.values():
                for key in get_ec2_keys(sg.id):
                    yield key

        # EC2 Snapshot, resource type ec2:snapshot
        for snapshot in self.ec2_backend.snapshots.values():
            for key in get_ec2_keys(snapshot.id):
                yield key

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        for volume in self.ec2_backend.volumes.values():
            for key in get_ec2_keys(volume.id):
                yield key

    def _get_tag_values_generator(self, tag_key):
        # Look at
        # https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html

        # Do S3, resource type s3
        for bucket in self.s3_backend.buckets.values():
            for tag in bucket.tags.tag_set.tags:
                if tag.key == tag_key:
                    yield tag.value

        # EC2 tags
        def get_ec2_values(res_id):
            result = []
            for key, value in self.ec2_backend.tags.get(res_id, {}).items():
                if key == tag_key:
                    result.append(value)
            return result

        # EC2 AMI, resource type ec2:image
        for ami in self.ec2_backend.amis.values():
            for value in get_ec2_values(ami.id):
                yield value

        # EC2 Instance, resource type ec2:instance
        for reservation in self.ec2_backend.reservations.values():
            for instance in reservation.instances:
                for value in get_ec2_values(instance.id):
                    yield value

        # EC2 NetworkInterface, resource type ec2:network-interface
        for eni in self.ec2_backend.enis.values():
            for value in get_ec2_values(eni.id):
                yield value

        # TODO EC2 ReservedInstance

        # EC2 SecurityGroup, resource type ec2:security-group
        for vpc in self.ec2_backend.groups.values():
            for sg in vpc.values():
                for value in get_ec2_values(sg.id):
                    yield value

        # EC2 Snapshot, resource type ec2:snapshot
        for snapshot in self.ec2_backend.snapshots.values():
            for value in get_ec2_values(snapshot.id):
                yield value

        # TODO EC2 SpotInstanceRequest

        # EC2 Volume, resource type ec2:volume
        for volume in self.ec2_backend.volumes.values():
            for value in get_ec2_values(volume.id):
                yield value

    def get_resources(self, pagination_token=None,
                      resources_per_page=50, tags_per_page=100,
                      tag_filters=None, resource_type_filters=None):
        # Simple range checning
        if 100 >= tags_per_page >= 500:
            raise RESTError('InvalidParameterException', 'TagsPerPage must be between 100 and 500')
        if 1 >= resources_per_page >= 50:
            raise RESTError('InvalidParameterException', 'ResourcesPerPage must be between 1 and 50')

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

    def get_tag_keys(self, pagination_token=None):

        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError('PaginationTokenExpiredException', 'Token does not exist')

            generator = self._pages[pagination_token]['gen']
            left_over = self._pages[pagination_token]['misc']
        else:
            generator = self._get_tag_keys_generator()
            left_over = None

        result = []
        current_tags = 0
        if left_over:
            result.append(left_over)
            current_tags += 1

        try:
            while True:
                # Generator format: ['tag', 'tag', 'tag', ...]
                next_item = six.next(generator)

                if current_tags + 1 >= 128:
                    break

                current_tags += 1

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

    def get_tag_values(self, pagination_token, key):

        if pagination_token:
            if pagination_token not in self._pages:
                raise RESTError('PaginationTokenExpiredException', 'Token does not exist')

            generator = self._pages[pagination_token]['gen']
            left_over = self._pages[pagination_token]['misc']
        else:
            generator = self._get_tag_values_generator(key)
            left_over = None

        result = []
        current_tags = 0
        if left_over:
            result.append(left_over)
            current_tags += 1

        try:
            while True:
                # Generator format: ['value', 'value', 'value', ...]
                next_item = six.next(generator)

                if current_tags + 1 >= 128:
                    break

                current_tags += 1

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

    # These methods will be called from responses.py.
    # They should call a tag function inside of the moto module
    # that governs the resource, that way if the target module
    # changes how tags are delt with theres less to change

    # def tag_resources(self, resource_arn_list, tags):
    #     return failed_resources_map
    #
    # def untag_resources(self, resource_arn_list, tag_keys):
    #     return failed_resources_map


available_regions = boto3.session.Session().get_available_regions("resourcegroupstaggingapi")
resourcegroupstaggingapi_backends = {region: ResourceGroupsTaggingAPIBackend(region) for region in available_regions}
