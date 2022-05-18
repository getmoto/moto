from collections import defaultdict

from moto.core.common_models import CloudFormationModel
from moto.packages.boto.ec2.launchspecification import LaunchSpecification
from moto.packages.boto.ec2.spotinstancerequest import (
    SpotInstanceRequest as BotoSpotRequest,
)
from .core import TaggedEC2Resource
from .instance_types import INSTANCE_TYPE_OFFERINGS
from ..utils import (
    random_spot_fleet_request_id,
    random_spot_request_id,
    generic_filter,
    convert_tag_spec,
)


class SpotInstanceRequest(BotoSpotRequest, TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        spot_request_id,
        price,
        image_id,
        spot_instance_type,
        valid_from,
        valid_until,
        launch_group,
        availability_zone_group,
        key_name,
        security_groups,
        user_data,
        instance_type,
        placement,
        kernel_id,
        ramdisk_id,
        monitoring_enabled,
        subnet_id,
        tags,
        spot_fleet_id,
        instance_interruption_behaviour,
        **kwargs,
    ):
        super().__init__(**kwargs)
        ls = LaunchSpecification()
        self.ec2_backend = ec2_backend
        self.launch_specification = ls
        self.id = spot_request_id
        self.state = "open"
        self.status = "pending-evaluation"
        self.status_message = "Your Spot request has been submitted for review, and is pending evaluation."
        if price:
            price = float(price)
            price = "{0:.6f}".format(price)  # round up/down to 6 decimals
        self.price = price
        self.type = spot_instance_type
        self.valid_from = valid_from
        self.valid_until = valid_until
        self.launch_group = launch_group
        self.availability_zone_group = availability_zone_group
        self.instance_interruption_behaviour = (
            instance_interruption_behaviour or "terminate"
        )
        self.user_data = user_data  # NOT
        ls.kernel = kernel_id
        ls.ramdisk = ramdisk_id
        ls.image_id = image_id
        ls.key_name = key_name
        ls.instance_type = instance_type
        ls.placement = placement
        ls.monitored = monitoring_enabled
        ls.subnet_id = subnet_id
        self.spot_fleet_id = spot_fleet_id
        tag_map = tags.get("spot-instances-request", {})
        self.add_tags(tag_map)
        self.all_tags = tags

        if security_groups:
            for group_name in security_groups:
                group = self.ec2_backend.get_security_group_by_name_or_id(group_name)
                if group:
                    ls.groups.append(group)
        else:
            # If not security groups, add the default
            default_group = self.ec2_backend.get_security_group_by_name_or_id("default")
            ls.groups.append(default_group)

        self.instance = self.launch_instance()
        self.state = "active"
        self.status = "fulfilled"
        self.status_message = ""

    def get_filter_value(self, filter_name):
        if filter_name == "state":
            return self.state
        elif filter_name == "spot-instance-request-id":
            return self.id
        else:
            return super().get_filter_value(filter_name, "DescribeSpotInstanceRequests")

    def launch_instance(self):
        reservation = self.ec2_backend.add_instances(
            image_id=self.launch_specification.image_id,
            count=1,
            user_data=self.user_data,
            instance_type=self.launch_specification.instance_type,
            is_instance_type_default=not self.launch_specification.instance_type,
            subnet_id=self.launch_specification.subnet_id,
            key_name=self.launch_specification.key_name,
            security_group_names=[],
            security_group_ids=self.launch_specification.groups,
            spot_fleet_id=self.spot_fleet_id,
            tags=self.all_tags,
            lifecycle="spot",
        )
        instance = reservation.instances[0]
        return instance


class SpotRequestBackend(object):
    def __init__(self):
        self.spot_instance_requests = {}
        super().__init__()

    def request_spot_instances(
        self,
        price,
        image_id,
        count,
        spot_instance_type,
        valid_from,
        valid_until,
        launch_group,
        availability_zone_group,
        key_name,
        security_groups,
        user_data,
        instance_type,
        placement,
        kernel_id,
        ramdisk_id,
        monitoring_enabled,
        subnet_id,
        tags=None,
        spot_fleet_id=None,
        instance_interruption_behaviour=None,
    ):
        requests = []
        tags = tags or {}
        for _ in range(count):
            spot_request_id = random_spot_request_id()
            request = SpotInstanceRequest(
                self,
                spot_request_id,
                price,
                image_id,
                spot_instance_type,
                valid_from,
                valid_until,
                launch_group,
                availability_zone_group,
                key_name,
                security_groups,
                user_data,
                instance_type,
                placement,
                kernel_id,
                ramdisk_id,
                monitoring_enabled,
                subnet_id,
                tags,
                spot_fleet_id,
                instance_interruption_behaviour,
            )
            self.spot_instance_requests[spot_request_id] = request
            requests.append(request)
        return requests

    def describe_spot_instance_requests(self, filters=None, spot_instance_ids=None):
        requests = self.spot_instance_requests.copy().values()

        if spot_instance_ids:
            requests = [i for i in requests if i.id in spot_instance_ids]

        return generic_filter(filters, requests)

    def cancel_spot_instance_requests(self, request_ids):
        requests = []
        for request_id in request_ids:
            requests.append(self.spot_instance_requests.pop(request_id))
        return requests


class SpotFleetLaunchSpec(object):
    def __init__(
        self,
        ebs_optimized,
        group_set,
        iam_instance_profile,
        image_id,
        instance_type,
        key_name,
        monitoring,
        spot_price,
        subnet_id,
        tag_specifications,
        user_data,
        weighted_capacity,
    ):
        self.ebs_optimized = ebs_optimized
        self.group_set = group_set
        self.iam_instance_profile = iam_instance_profile
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.monitoring = monitoring
        self.spot_price = spot_price
        self.subnet_id = subnet_id
        self.tag_specifications = tag_specifications
        self.user_data = user_data
        self.weighted_capacity = float(weighted_capacity)


class SpotFleetRequest(TaggedEC2Resource, CloudFormationModel):
    def __init__(
        self,
        ec2_backend,
        spot_fleet_request_id,
        spot_price,
        target_capacity,
        iam_fleet_role,
        allocation_strategy,
        launch_specs,
        launch_template_config,
        instance_interruption_behaviour,
    ):

        self.ec2_backend = ec2_backend
        self.id = spot_fleet_request_id
        self.spot_price = spot_price
        self.target_capacity = int(target_capacity)
        self.iam_fleet_role = iam_fleet_role
        self.allocation_strategy = allocation_strategy
        self.instance_interruption_behaviour = (
            instance_interruption_behaviour or "terminate"
        )
        self.state = "active"
        self.fulfilled_capacity = 0.0

        self.launch_specs = []

        launch_specs_from_config = []
        for config in launch_template_config or []:
            spec = config["LaunchTemplateSpecification"]
            if "LaunchTemplateId" in spec:
                launch_template = self.ec2_backend.get_launch_template(
                    template_id=spec["LaunchTemplateId"]
                )
            elif "LaunchTemplateName" in spec:
                launch_template = self.ec2_backend.get_launch_template_by_name(
                    name=spec["LaunchTemplateName"]
                )
            else:
                continue
            launch_template_data = launch_template.latest_version().data
            new_launch_template = launch_template_data.copy()
            if config.get("Overrides"):
                overrides = list(config["Overrides"].values())[0]
                new_launch_template.update(overrides)
            launch_specs_from_config.append(new_launch_template)

        for spec in (launch_specs or []) + launch_specs_from_config:
            tag_spec_set = spec.get("TagSpecificationSet", [])
            tags = convert_tag_spec(tag_spec_set)
            self.launch_specs.append(
                SpotFleetLaunchSpec(
                    ebs_optimized=spec.get("EbsOptimized"),
                    group_set=spec.get("GroupSet", []),
                    iam_instance_profile=spec.get("IamInstanceProfile"),
                    image_id=spec["ImageId"],
                    instance_type=spec["InstanceType"],
                    key_name=spec.get("KeyName"),
                    monitoring=spec.get("Monitoring"),
                    spot_price=spec.get("SpotPrice", self.spot_price),
                    subnet_id=spec.get("SubnetId"),
                    tag_specifications=tags,
                    user_data=spec.get("UserData"),
                    weighted_capacity=spec.get("WeightedCapacity", 1),
                )
            )

        self.spot_requests = []
        self.create_spot_requests(self.target_capacity)

    @property
    def physical_resource_id(self):
        return self.id

    @staticmethod
    def cloudformation_name_type():
        return None

    @staticmethod
    def cloudformation_type():
        # https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ec2-spotfleet.html
        return "AWS::EC2::SpotFleet"

    @classmethod
    def create_from_cloudformation_json(
        cls, resource_name, cloudformation_json, region_name, **kwargs
    ):
        from ..models import ec2_backends

        properties = cloudformation_json["Properties"]["SpotFleetRequestConfigData"]
        ec2_backend = ec2_backends[region_name]

        spot_price = properties.get("SpotPrice")
        target_capacity = properties["TargetCapacity"]
        iam_fleet_role = properties["IamFleetRole"]
        allocation_strategy = properties["AllocationStrategy"]
        launch_specs = properties["LaunchSpecifications"]

        spot_fleet_request = ec2_backend.request_spot_fleet(
            spot_price,
            target_capacity,
            iam_fleet_role,
            allocation_strategy,
            launch_specs,
        )

        return spot_fleet_request

    def get_launch_spec_counts(self, weight_to_add):
        weight_map = defaultdict(int)

        weight_so_far = 0
        if self.allocation_strategy == "diversified":
            launch_spec_index = 0
            while True:
                launch_spec = self.launch_specs[
                    launch_spec_index % len(self.launch_specs)
                ]
                weight_map[launch_spec] += 1
                weight_so_far += launch_spec.weighted_capacity
                if weight_so_far >= weight_to_add:
                    break
                launch_spec_index += 1
        else:  # lowestPrice
            cheapest_spec = sorted(
                # FIXME: change `+inf` to the on demand price scaled to weighted capacity when it's not present
                self.launch_specs,
                key=lambda spec: float(spec.spot_price or "+inf"),
            )[0]
            weight_so_far = weight_to_add + (
                weight_to_add % cheapest_spec.weighted_capacity
            )
            weight_map[cheapest_spec] = int(
                weight_so_far // cheapest_spec.weighted_capacity
            )

        return weight_map, weight_so_far

    def create_spot_requests(self, weight_to_add):
        weight_map, added_weight = self.get_launch_spec_counts(weight_to_add)
        for launch_spec, count in weight_map.items():
            requests = self.ec2_backend.request_spot_instances(
                price=launch_spec.spot_price,
                image_id=launch_spec.image_id,
                count=count,
                spot_instance_type="persistent",
                valid_from=None,
                valid_until=None,
                launch_group=None,
                availability_zone_group=None,
                key_name=launch_spec.key_name,
                security_groups=launch_spec.group_set,
                user_data=launch_spec.user_data,
                instance_type=launch_spec.instance_type,
                placement=None,
                kernel_id=None,
                ramdisk_id=None,
                monitoring_enabled=launch_spec.monitoring,
                subnet_id=launch_spec.subnet_id,
                spot_fleet_id=self.id,
                tags=launch_spec.tag_specifications,
            )
            self.spot_requests.extend(requests)
        self.fulfilled_capacity += added_weight
        return self.spot_requests

    def terminate_instances(self):
        instance_ids = []
        new_fulfilled_capacity = self.fulfilled_capacity
        for req in self.spot_requests:
            instance = req.instance
            for spec in self.launch_specs:
                if (
                    spec.instance_type == instance.instance_type
                    and spec.subnet_id == instance.subnet_id
                ):
                    break

            if new_fulfilled_capacity - spec.weighted_capacity < self.target_capacity:
                continue
            new_fulfilled_capacity -= spec.weighted_capacity
            instance_ids.append(instance.id)

        self.spot_requests = [
            req for req in self.spot_requests if req.instance.id not in instance_ids
        ]
        self.ec2_backend.terminate_instances(instance_ids)


class SpotFleetBackend(object):
    def __init__(self):
        self.spot_fleet_requests = {}
        super().__init__()

    def request_spot_fleet(
        self,
        spot_price,
        target_capacity,
        iam_fleet_role,
        allocation_strategy,
        launch_specs,
        launch_template_config=None,
        instance_interruption_behaviour=None,
    ):

        spot_fleet_request_id = random_spot_fleet_request_id()
        request = SpotFleetRequest(
            self,
            spot_fleet_request_id,
            spot_price,
            target_capacity,
            iam_fleet_role,
            allocation_strategy,
            launch_specs,
            launch_template_config,
            instance_interruption_behaviour,
        )
        self.spot_fleet_requests[spot_fleet_request_id] = request
        return request

    def get_spot_fleet_request(self, spot_fleet_request_id):
        return self.spot_fleet_requests[spot_fleet_request_id]

    def describe_spot_fleet_instances(self, spot_fleet_request_id):
        spot_fleet = self.get_spot_fleet_request(spot_fleet_request_id)
        return spot_fleet.spot_requests

    def describe_spot_fleet_requests(self, spot_fleet_request_ids):
        requests = self.spot_fleet_requests.values()

        if spot_fleet_request_ids:
            requests = [
                request for request in requests if request.id in spot_fleet_request_ids
            ]

        return requests

    def cancel_spot_fleet_requests(self, spot_fleet_request_ids, terminate_instances):
        spot_requests = []
        for spot_fleet_request_id in spot_fleet_request_ids:
            spot_fleet = self.spot_fleet_requests[spot_fleet_request_id]
            if terminate_instances:
                spot_fleet.target_capacity = 0
                spot_fleet.terminate_instances()
            spot_requests.append(spot_fleet)
            del self.spot_fleet_requests[spot_fleet_request_id]
        return spot_requests

    def modify_spot_fleet_request(
        self, spot_fleet_request_id, target_capacity, terminate_instances
    ):
        if target_capacity < 0:
            raise ValueError("Cannot reduce spot fleet capacity below 0")
        spot_fleet_request = self.spot_fleet_requests[spot_fleet_request_id]
        delta = target_capacity - spot_fleet_request.fulfilled_capacity
        spot_fleet_request.target_capacity = target_capacity
        if delta > 0:
            spot_fleet_request.create_spot_requests(delta)
        elif delta < 0 and terminate_instances == "Default":
            spot_fleet_request.terminate_instances()
        return True


class SpotPriceBackend(object):
    def describe_spot_price_history(self, instance_types=None, filters=None):
        matches = INSTANCE_TYPE_OFFERINGS["availability-zone"]
        matches = matches.get(self.region_name, [])

        def matches_filters(offering, filters):
            def matches_filter(key, values):
                if key == "availability-zone":
                    return offering.get("Location") in values
                elif key == "instance-type":
                    return offering.get("InstanceType") in values
                else:
                    return False

            return all([matches_filter(key, values) for key, values in filters.items()])

        matches = [o for o in matches if matches_filters(o, filters)]

        if instance_types:
            matches = [t for t in matches if t.get("InstanceType") in instance_types]

        return matches
