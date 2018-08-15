from __future__ import unicode_literals
from moto.core.responses import BaseResponse


class ReservedInstances(BaseResponse):

    def cancel_reserved_instances_listing(self):
        if self.is_not_dryrun('CancelReservedInstances'):
            raise NotImplementedError(
                'ReservedInstances.cancel_reserved_instances_listing is not yet implemented')

    def create_reserved_instances_listing(self):
        if self.is_not_dryrun('CreateReservedInstances'):
            raise NotImplementedError(
                'ReservedInstances.create_reserved_instances_listing is not yet implemented')

    def describe_reserved_instances(self):
        raise NotImplementedError(
            'ReservedInstances.describe_reserved_instances is not yet implemented')

    def describe_reserved_instances_listings(self):
        raise NotImplementedError(
            'ReservedInstances.describe_reserved_instances_listings is not yet implemented')

    def describe_reserved_instances_offerings(self):
        region = self.region
        instance_type = self._get_param("InstanceType")
        product_description = self._get_param("ProductDescription")
        product_description = self._get_param("ProductDescription")
        instance_tenancy = self._get_param("InstanceTenancy")
        offering_class = self._get_param("OfferingClass")
        offering_type = self._get_param("OfferingType")
        max_duration = self._get_param("MaxDuration")
        min_duration = self._get_param("MinDuration")
        reserved_instances_offering_id = self._get_multi_param("ReservedInstancesOfferingId")

        offerings = self.ec2_backend.get_offering_ids(reserved_instances_offering_id, instance_type=instance_type, description=product_description,
            instance_tenancy=instance_tenancy, offering_class=offering_class, offering_type=offering_type,
            max_duration=max_duration, min_duration=min_duration, region=region)

        template = self.response_template(EC2_DESCRIBE_RESERVED_INSTANCE_OFFERINGS)
        return template.render(offerings=offerings)

    def purchase_reserved_instances_offering(self):
        region = self.region
        reserved_instances_offering_id = self._get_param("ReservedInstancesOfferingId")
        instance_count = self._get_param("InstanceCount")

        reserved_instance = self.ec2_backend.purchase_reserved_instances(reserved_instances_offering_id, instance_count, region=region)
        template = self.response_template(EC2_PURCHASE_RESERVED_INSTANCES_OFFERING)
        return template.render(reserved_instance=reserved_instance)


EC2_DESCRIBE_RESERVED_INSTANCE_OFFERINGS = """<DescribeReservedInstancesOfferingsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>fdcdcab1-ae5c-489e-9c33-4637c5dda355</requestId>
  <reservedInstancesOfferingsSet>
    {% for offering in offerings %}
      <item>
        <reservedInstancesOfferingId>{{ offering.id }}</reservedInstancesOfferingId>
        <instanceType>{{ offering.instance_type }}</instanceType>
        {% if offering.scope == "Availability Zone" %}
            <availabilityZone>{{ offering.availability_zone }}</availabilityZone>
        {% endif %}
        <duration>{{ offering.duration }}</duration>
        <fixedPrice>{{ offering.fixed_price }}</fixedPrice>
        <usagePrice>{{ offering.usage_price }}</usagePrice>
        <productDescription>{{ offering.description }}</productDescription>
        <instanceTenancy>{{ offering.instance_tenancy }}</instanceTenancy>
        <currencyCode>{{ offering.currency_code }}</currencyCode>
        <recurringCharges>
          <item>
            <frequency>{{ offering.frequency }}</frequency>
            <amount>{{ offering.amount }}</amount>
          </item>
        </recurringCharges>
        <marketplace>{{ offering.marketplace }}</marketplace>
        <offeringType>{{ offering.offering_type }}</offeringType>
        <offeringClass>{{ offering.offering_class }}</offeringClass>
        <pricingDetailsSet>[]</pricingDetailsSet>
        <scope>{{ offering.scope }}</scope>
      </item>
    {% endfor %}
  </reservedInstancesOfferingsSet>
</DescribeReservedInstancesOfferingsResponse>"""

EC2_PURCHASE_RESERVED_INSTANCES_OFFERING = """<PurchaseReservedInstancesOfferingResponse  xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>69dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <reservedInstancesId>{{ reserved_instance.id }}</reservedInstancesId>
  </PurchaseReservedInstancesOfferingResponse>"""
