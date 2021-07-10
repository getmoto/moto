from moto.core.responses import BaseResponse


class PrefixList(BaseResponse):
    def create_managed_prefix_list(self):
        name = self._get_param("AddressFamily")
        max_entries = self._get_param("MaxEntries")
        prefix_list_name = self._get_param("PrefixListName")
        entries = self._get_multi_param("Entry")
        prefix_list = self.ec2_backend.create_managed_prefix_list(
            name, max_entries, prefix_list_name, entries
        )
        template = self.response_template(CREATE_MANAGED_PREFIX_LIST_RESPONSE)
        return template.render(prefix_list=prefix_list)


CREATE_MANAGED_PREFIX_LIST_RESPONSE = """
<CreateManagedPrefixListResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <prefixList>
        <prefixListId> {{ prefix_list.id }} </prefixListId>
        <addressFamily> {{ prefix_list.address_family }} </addressFamily>
        <state> create-in-progress </state>
        <prefixListName> {{ prefix_list.prefix_list_name }} </prefixListName>
        <maxEntries> {{ prefix_list.max_entries }} </maxEntries>
        <version> 1 </version>
        <prefixListArn> {{ prefix_list.arn }} </prefixListArn>
        <ownerId> {{ prefix_list.owner_id }} </ownerId>
   </prefixList>
</CreateManagedPrefixListResponse>
"""
