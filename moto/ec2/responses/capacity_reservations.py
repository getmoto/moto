from moto.core.responses import ActionResult
from moto.ec2.utils import add_tag_specification
from moto.utilities.utils import str2bool

from ._base_response import EC2BaseResponse


class CapacityReservations(EC2BaseResponse):
    def create_capacity_reservation(self) -> ActionResult:
        instance_type = self._get_param("InstanceType")
        instance_platform = self._get_param("InstancePlatform")
        availability_zone = self._get_param("AvailabilityZone")
        instance_count = int(self._get_param("InstanceCount", "1"))
        tenancy = self._get_param("Tenancy", "default")
        ebs_optimized = str2bool(
            self._get_param("EbsOptimized", "false")
        )
        ephemeral_storage = str2bool(
            self._get_param("EphemeralStorage", "false")
        )
        end_date = self._get_param("EndDate")
        end_date_type = self._get_param("EndDateType", "unlimited")
        instance_match_criteria = self._get_param(
            "InstanceMatchCriteria", "open"
        )
        tags = add_tag_specification(
            self._get_param("TagSpecifications", [])
        )

        cr = self.ec2_backend.create_capacity_reservation(
            instance_type=instance_type,
            instance_platform=instance_platform,
            availability_zone=availability_zone,
            instance_count=instance_count,
            tenancy=tenancy,
            ebs_optimized=ebs_optimized,
            ephemeral_storage=ephemeral_storage,
            end_date=end_date,
            end_date_type=end_date_type,
            instance_match_criteria=instance_match_criteria,
            tags=tags,
        )
        return ActionResult({"CapacityReservation": cr})

    def describe_capacity_reservations(self) -> ActionResult:
        cr_ids = self._get_param("CapacityReservationId", [])
        crs = self.ec2_backend.describe_capacity_reservations(
            capacity_reservation_ids=cr_ids or None,
        )
        return ActionResult({"CapacityReservations": crs})

    def modify_capacity_reservation(self) -> ActionResult:
        cr_id = self._get_param("CapacityReservationId")
        instance_count = self._get_param("InstanceCount")
        end_date = self._get_param("EndDate")
        end_date_type = self._get_param("EndDateType")
        self.ec2_backend.modify_capacity_reservation(
            capacity_reservation_id=cr_id,
            instance_count=(
                int(instance_count) if instance_count else None
            ),
            end_date=end_date,
            end_date_type=end_date_type,
        )
        return ActionResult({"Return": True})

    def cancel_capacity_reservation(self) -> ActionResult:
        cr_id = self._get_param("CapacityReservationId")
        self.ec2_backend.cancel_capacity_reservation(
            capacity_reservation_id=cr_id,
        )
        return ActionResult({"Return": True})

    def create_capacity_reservation_fleet(self) -> ActionResult:
        specs = self._get_param("InstanceTypeSpecification", [])
        total = int(self._get_param("TotalTargetCapacity", "1"))
        alloc = self._get_param("AllocationStrategy", "prioritized")
        tenancy = self._get_param("Tenancy", "default")
        end_date = self._get_param("EndDate")
        match = self._get_param("InstanceMatchCriteria", "open")
        tags = add_tag_specification(
            self._get_param("TagSpecifications", [])
        )

        fleet = self.ec2_backend.create_capacity_reservation_fleet(
            instance_type_specifications=specs,
            total_target_capacity=total,
            allocation_strategy=alloc,
            tenancy=tenancy,
            end_date=end_date,
            instance_match_criteria=match,
            tags=tags,
        )
        return ActionResult({"CapacityReservationFleet": fleet})

    def describe_capacity_reservation_fleets(self) -> ActionResult:
        fleet_ids = self._get_param(
            "CapacityReservationFleetId", []
        )
        fleets = self.ec2_backend.describe_capacity_reservation_fleets(
            capacity_reservation_fleet_ids=fleet_ids or None,
        )
        return ActionResult({"CapacityReservationFleets": fleets})

    def modify_capacity_reservation_fleet(self) -> ActionResult:
        fleet_id = self._get_param("CapacityReservationFleetId")
        total = self._get_param("TotalTargetCapacity")
        end_date = self._get_param("EndDate")
        self.ec2_backend.modify_capacity_reservation_fleet(
            capacity_reservation_fleet_id=fleet_id,
            total_target_capacity=(
                int(total) if total else None
            ),
            end_date=end_date,
        )
        return ActionResult({"Return": True})

    def cancel_capacity_reservation_fleets(self) -> ActionResult:
        fleet_ids = self._get_param(
            "CapacityReservationFleetId", []
        )
        results = self.ec2_backend.cancel_capacity_reservation_fleets(
            capacity_reservation_fleet_ids=fleet_ids,
        )
        successful_fleets = [r for r in results if "error" not in r]
        return ActionResult(
            {
                "SuccessfulFleetCancellations": successful_fleets,
                "FailedFleetCancellations": [],
            }
        )


CREATE_CAPACITY_RESERVATION = """<CreateCapacityReservationResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <capacityReservation>
    <capacityReservationId>{{ cr.id }}</capacityReservationId>
    <ownerId>{{ cr.owner_id }}</ownerId>
    <capacityReservationArn>{{ cr.arn }}</capacityReservationArn>
    <instanceType>{{ cr.instance_type }}</instanceType>
    <instancePlatform>{{ cr.instance_platform }}</instancePlatform>
    <availabilityZone>{{ cr.availability_zone }}</availabilityZone>
    <tenancy>{{ cr.tenancy }}</tenancy>
    <totalInstanceCount>{{ cr.total_instance_count }}</totalInstanceCount>
    <availableInstanceCount>{{ cr.available_instance_count }}</availableInstanceCount>
    <ebsOptimized>{{ 'true' if cr.ebs_optimized else 'false' }}</ebsOptimized>
    <ephemeralStorage>{{ 'true' if cr.ephemeral_storage else 'false' }}</ephemeralStorage>
    <state>{{ cr.state }}</state>
    <endDateType>{{ cr.end_date_type }}</endDateType>
    <instanceMatchCriteria>{{ cr.instance_match_criteria }}</instanceMatchCriteria>
    <createDate>{{ cr.creation_date }}</createDate>
    <tagSet>
      {% for tag in cr.get_tags() %}
      <item>
        <key>{{ tag.key }}</key>
        <value>{{ tag.value }}</value>
      </item>
      {% endfor %}
    </tagSet>
  </capacityReservation>
</CreateCapacityReservationResponse>"""

DESCRIBE_CAPACITY_RESERVATIONS = """<DescribeCapacityReservationsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <capacityReservationSet>
    {% for cr in reservations %}
    <item>
      <capacityReservationId>{{ cr.id }}</capacityReservationId>
      <ownerId>{{ cr.owner_id }}</ownerId>
      <capacityReservationArn>{{ cr.arn }}</capacityReservationArn>
      <instanceType>{{ cr.instance_type }}</instanceType>
      <instancePlatform>{{ cr.instance_platform }}</instancePlatform>
      <availabilityZone>{{ cr.availability_zone }}</availabilityZone>
      <tenancy>{{ cr.tenancy }}</tenancy>
      <totalInstanceCount>{{ cr.total_instance_count }}</totalInstanceCount>
      <availableInstanceCount>{{ cr.available_instance_count }}</availableInstanceCount>
      <ebsOptimized>{{ 'true' if cr.ebs_optimized else 'false' }}</ebsOptimized>
      <ephemeralStorage>{{ 'true' if cr.ephemeral_storage else 'false' }}</ephemeralStorage>
      <state>{{ cr.state }}</state>
      <endDateType>{{ cr.end_date_type }}</endDateType>
      <instanceMatchCriteria>{{ cr.instance_match_criteria }}</instanceMatchCriteria>
      <createDate>{{ cr.creation_date }}</createDate>
      <tagSet>
        {% for tag in cr.get_tags() %}
        <item>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
        {% endfor %}
      </tagSet>
    </item>
    {% endfor %}
  </capacityReservationSet>
</DescribeCapacityReservationsResponse>"""

MODIFY_CAPACITY_RESERVATION = """<ModifyCapacityReservationResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</ModifyCapacityReservationResponse>"""

CANCEL_CAPACITY_RESERVATION = """<CancelCapacityReservationResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</CancelCapacityReservationResponse>"""

CREATE_CAPACITY_RESERVATION_FLEET = """<CreateCapacityReservationFleetResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <capacityReservationFleetId>{{ fleet.id }}</capacityReservationFleetId>
  <state>{{ fleet.state }}</state>
  <totalTargetCapacity>{{ fleet.total_target_capacity }}</totalTargetCapacity>
  <totalFulfilledCapacity>{{ fleet.total_fulfilled_capacity }}</totalFulfilledCapacity>
  <allocationStrategy>{{ fleet.allocation_strategy }}</allocationStrategy>
  <createTime>{{ fleet.creation_time }}</createTime>
</CreateCapacityReservationFleetResponse>"""

DESCRIBE_CAPACITY_RESERVATION_FLEETS = """<DescribeCapacityReservationFleetsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <capacityReservationFleetSet>
    {% for fleet in fleets %}
    <item>
      <capacityReservationFleetId>{{ fleet.id }}</capacityReservationFleetId>
      <state>{{ fleet.state }}</state>
      <totalTargetCapacity>{{ fleet.total_target_capacity }}</totalTargetCapacity>
      <totalFulfilledCapacity>{{ fleet.total_fulfilled_capacity }}</totalFulfilledCapacity>
      <allocationStrategy>{{ fleet.allocation_strategy }}</allocationStrategy>
      <tenancy>{{ fleet.tenancy }}</tenancy>
      <createTime>{{ fleet.creation_time }}</createTime>
    </item>
    {% endfor %}
  </capacityReservationFleetSet>
</DescribeCapacityReservationFleetsResponse>"""

MODIFY_CAPACITY_RESERVATION_FLEET = """<ModifyCapacityReservationFleetResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <return>true</return>
</ModifyCapacityReservationFleetResponse>"""

CANCEL_CAPACITY_RESERVATION_FLEETS = """<CancelCapacityReservationFleetsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <successfulFleetCancellationSet>
    {% for r in results %}
    {% if 'error' not in r %}
    <item>
      <capacityReservationFleetId>{{ r.capacity_reservation_fleet_id }}</capacityReservationFleetId>
      <currentFleetState>{{ r.current_state }}</currentFleetState>
      <previousFleetState>{{ r.previous_state }}</previousFleetState>
    </item>
    {% endif %}
    {% endfor %}
  </successfulFleetCancellationSet>
  <failedFleetCancellationSet/>
</CancelCapacityReservationFleetsResponse>"""
