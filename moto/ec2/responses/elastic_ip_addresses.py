from moto.core.responses import BaseResponse
from moto.ec2.utils import filters_from_querystring, add_tag_specification


class ElasticIPAddresses(BaseResponse):
    def allocate_address(self):
        domain = self._get_param("Domain", if_none="standard")
        reallocate_address = self._get_param("Address", if_none=None)
        tags = self._get_multi_param("TagSpecification")
        tags = add_tag_specification(tags)

        if self.is_not_dryrun("AllocateAddress"):
            if reallocate_address:
                address = self.ec2_backend.allocate_address(
                    domain, address=reallocate_address, tags=tags
                )
            else:
                address = self.ec2_backend.allocate_address(domain, tags=tags)
            template = self.response_template(ALLOCATE_ADDRESS_RESPONSE)
            return template.render(address=address)

    def associate_address(self):
        instance = eni = None

        if "InstanceId" in self.querystring:
            instance = self.ec2_backend.get_instance(self._get_param("InstanceId"))
        elif "NetworkInterfaceId" in self.querystring:
            eni = self.ec2_backend.get_network_interface(
                self._get_param("NetworkInterfaceId")
            )
        else:
            self.ec2_backend.raise_error(
                "MissingParameter",
                "Invalid request, expect InstanceId/NetworkId parameter.",
            )

        reassociate = False
        if "AllowReassociation" in self.querystring:
            reassociate = self._get_param("AllowReassociation") == "true"

        if self.is_not_dryrun("AssociateAddress"):
            if instance or eni:
                if "PublicIp" in self.querystring:
                    eip = self.ec2_backend.associate_address(
                        instance=instance,
                        eni=eni,
                        address=self._get_param("PublicIp"),
                        reassociate=reassociate,
                    )
                elif "AllocationId" in self.querystring:
                    eip = self.ec2_backend.associate_address(
                        instance=instance,
                        eni=eni,
                        allocation_id=self._get_param("AllocationId"),
                        reassociate=reassociate,
                    )
                else:
                    self.ec2_backend.raise_error(
                        "MissingParameter",
                        "Invalid request, expect PublicIp/AllocationId parameter.",
                    )
            else:
                self.ec2_backend.raise_error(
                    "MissingParameter",
                    "Invalid request, expect either instance or ENI.",
                )

            template = self.response_template(ASSOCIATE_ADDRESS_RESPONSE)
            return template.render(address=eip)

    def describe_addresses(self):
        self.error_on_dryrun()
        allocation_ids = self._get_multi_param("AllocationId")
        public_ips = self._get_multi_param("PublicIp")
        filters = filters_from_querystring(self.querystring)
        addresses = self.ec2_backend.describe_addresses(
            allocation_ids, public_ips, filters
        )
        template = self.response_template(DESCRIBE_ADDRESS_RESPONSE)
        return template.render(addresses=addresses)

    def disassociate_address(self):
        if self.is_not_dryrun("DisAssociateAddress"):
            if "PublicIp" in self.querystring:
                self.ec2_backend.disassociate_address(
                    address=self._get_param("PublicIp")
                )
            elif "AssociationId" in self.querystring:
                self.ec2_backend.disassociate_address(
                    association_id=self._get_param("AssociationId")
                )
            else:
                self.ec2_backend.raise_error(
                    "MissingParameter",
                    "Invalid request, expect PublicIp/AssociationId parameter.",
                )

            return self.response_template(DISASSOCIATE_ADDRESS_RESPONSE).render()

    def release_address(self):
        if self.is_not_dryrun("ReleaseAddress"):
            if "PublicIp" in self.querystring:
                self.ec2_backend.release_address(address=self._get_param("PublicIp"))
            elif "AllocationId" in self.querystring:
                self.ec2_backend.release_address(
                    allocation_id=self._get_param("AllocationId")
                )
            else:
                self.ec2_backend.raise_error(
                    "MissingParameter",
                    "Invalid request, expect PublicIp/AllocationId parameter.",
                )

            return self.response_template(RELEASE_ADDRESS_RESPONSE).render()


ALLOCATE_ADDRESS_RESPONSE = """<AllocateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <publicIp>{{ address.public_ip }}</publicIp>
  <domain>{{ address.domain }}</domain>
  {% if address.allocation_id %}
    <allocationId>{{ address.allocation_id }}</allocationId>
  {% endif %}
</AllocateAddressResponse>"""

ASSOCIATE_ADDRESS_RESPONSE = """<AssociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
  {% if address.association_id %}
    <associationId>{{ address.association_id }}</associationId>
  {% endif %}
</AssociateAddressResponse>"""

DESCRIBE_ADDRESS_RESPONSE = """<DescribeAddressesResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <addressesSet>
    {% for address in addresses %}
        <item>
          <publicIp>{{ address.public_ip }}</publicIp>
          <domain>{{ address.domain }}</domain>
          {% if address.instance %}
            <instanceId>{{ address.instance.id }}</instanceId>
          {% else %}
            <instanceId/>
          {% endif %}
          {% if address.eni %}
            <networkInterfaceId>{{ address.eni.id }}</networkInterfaceId>
          {% else %}
            <networkInterfaceId/>
          {% endif %}
          {% if address.allocation_id %}
            <allocationId>{{ address.allocation_id }}</allocationId>
          {% endif %}
          {% if address.association_id %}
            <associationId>{{ address.association_id }}</associationId>
          {% endif %}
          <tagSet>
          {% for tag in address.get_tags() %}
              <item>
                  <key>{{ tag.key }}</key>
                  <value>{{ tag.value }}</value>
              </item>
          {% endfor %}
          </tagSet>
        </item>
    {% endfor %}
  </addressesSet>
</DescribeAddressesResponse>"""

DISASSOCIATE_ADDRESS_RESPONSE = """<DisassociateAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</DisassociateAddressResponse>"""

RELEASE_ADDRESS_RESPONSE = """<ReleaseAddressResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>true</return>
</ReleaseAddressResponse>"""
