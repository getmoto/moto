from moto.core.responses import ActionResult
from moto.ec2.utils import add_tag_specification
from moto.utilities.utils import str2bool

from ._base_response import EC2BaseResponse


class TransitGatewayConnectResponse(EC2BaseResponse):
    def create_transit_gateway_connect(self) -> ActionResult:
        transport_tgw_attachment_id = self._get_param(
            "TransportTransitGatewayAttachmentId"
        )
        options = self._get_param("Options", {})
        tags = add_tag_specification(self._get_param("TagSpecifications", []))

        connect = self.ec2_backend.create_transit_gateway_connect(
            transport_transit_gateway_attachment_id=transport_tgw_attachment_id,
            options=options,
            tags=tags,
        )
        return ActionResult({"TransitGatewayConnect": connect})

    def delete_transit_gateway_connect(self) -> ActionResult:
        tgw_attachment_id = self._get_param("TransitGatewayAttachmentId")
        connect = self.ec2_backend.delete_transit_gateway_connect(tgw_attachment_id)
        return ActionResult({"TransitGatewayConnect": connect})

    def describe_transit_gateway_connects(self) -> ActionResult:
        tgw_attachment_ids = self._get_param("TransitGatewayAttachmentIds", [])
        filters = self._filters_from_querystring()
        connects = self.ec2_backend.describe_transit_gateway_connects(
            transit_gateway_attachment_ids=tgw_attachment_ids or None,
            filters=filters,
        )
        return ActionResult({"TransitGatewayConnects": connects})

    def create_transit_gateway_connect_peer(self) -> ActionResult:
        tgw_attachment_id = self._get_param("TransitGatewayAttachmentId")
        tgw_address = self._get_param("TransitGatewayAddress")
        peer_address = self._get_param("PeerAddress", "")
        bgp_options = self._get_param("BgpOptions", {})
        inside_cidr_blocks = self._get_param("InsideCidrBlocks", [])
        tags = add_tag_specification(self._get_param("TagSpecifications", []))

        peer = self.ec2_backend.create_transit_gateway_connect_peer(
            transit_gateway_attachment_id=tgw_attachment_id,
            transit_gateway_address=tgw_address,
            peer_address=peer_address,
            bgp_options=bgp_options,
            inside_cidr_blocks=inside_cidr_blocks,
            tags=tags,
        )
        return ActionResult({"TransitGatewayConnectPeer": peer})

    def delete_transit_gateway_connect_peer(self) -> ActionResult:
        peer_id = self._get_param("TransitGatewayConnectPeerId")
        peer = self.ec2_backend.delete_transit_gateway_connect_peer(peer_id)
        return ActionResult({"TransitGatewayConnectPeer": peer})

    def describe_transit_gateway_connect_peers(self) -> ActionResult:
        peer_ids = self._get_param("TransitGatewayConnectPeerIds", [])
        filters = self._filters_from_querystring()
        peers = self.ec2_backend.describe_transit_gateway_connect_peers(
            transit_gateway_connect_peer_ids=peer_ids or None,
            filters=filters,
        )
        return ActionResult({"TransitGatewayConnectPeers": peers})

    def create_transit_gateway_prefix_list_reference(self) -> ActionResult:
        tgw_rt_id = self._get_param("TransitGatewayRouteTableId")
        prefix_list_id = self._get_param("PrefixListId")
        tgw_attachment_id = self._get_param("TransitGatewayAttachmentId")
        blackhole = str2bool(self._get_param("Blackhole", "false"))

        ref = self.ec2_backend.create_transit_gateway_prefix_list_reference(
            transit_gateway_route_table_id=tgw_rt_id,
            prefix_list_id=prefix_list_id,
            transit_gateway_attachment_id=tgw_attachment_id,
            blackhole=blackhole,
        )
        return ActionResult({"TransitGatewayPrefixListReference": ref})

    def delete_transit_gateway_prefix_list_reference(self) -> ActionResult:
        tgw_rt_id = self._get_param("TransitGatewayRouteTableId")
        prefix_list_id = self._get_param("PrefixListId")

        ref = self.ec2_backend.delete_transit_gateway_prefix_list_reference(
            transit_gateway_route_table_id=tgw_rt_id,
            prefix_list_id=prefix_list_id,
        )
        return ActionResult({"TransitGatewayPrefixListReference": ref})

    def get_transit_gateway_prefix_list_references(self) -> ActionResult:
        tgw_rt_id = self._get_param("TransitGatewayRouteTableId")
        filters = self._filters_from_querystring()

        refs = self.ec2_backend.get_transit_gateway_prefix_list_references(
            transit_gateway_route_table_id=tgw_rt_id,
            filters=filters,
        )
        return ActionResult({"TransitGatewayPrefixListReferences": refs})


CREATE_TRANSIT_GATEWAY_CONNECT = """<CreateTransitGatewayConnectResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnect>
    <transitGatewayAttachmentId>{{ connect.id }}</transitGatewayAttachmentId>
    <transportTransitGatewayAttachmentId>{{ connect.transport_transit_gateway_attachment_id }}</transportTransitGatewayAttachmentId>
    <transitGatewayId>{{ connect.transit_gateway_id }}</transitGatewayId>
    <state>{{ connect.state }}</state>
    <creationTime>{{ connect.creation_time }}</creationTime>
    <options>
      <protocol>{{ connect.options.get('Protocol', 'gre') }}</protocol>
    </options>
    <tagSet>
      {% for tag in connect.get_tags() %}
      <item>
        <key>{{ tag.key }}</key>
        <value>{{ tag.value }}</value>
      </item>
      {% endfor %}
    </tagSet>
  </transitGatewayConnect>
</CreateTransitGatewayConnectResponse>"""


DELETE_TRANSIT_GATEWAY_CONNECT = """<DeleteTransitGatewayConnectResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnect>
    <transitGatewayAttachmentId>{{ connect.id }}</transitGatewayAttachmentId>
    <state>{{ connect.state }}</state>
  </transitGatewayConnect>
</DeleteTransitGatewayConnectResponse>"""


DESCRIBE_TRANSIT_GATEWAY_CONNECTS = """<DescribeTransitGatewayConnectsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnectSet>
    {% for connect in connects %}
    <item>
      <transitGatewayAttachmentId>{{ connect.id }}</transitGatewayAttachmentId>
      <transportTransitGatewayAttachmentId>{{ connect.transport_transit_gateway_attachment_id }}</transportTransitGatewayAttachmentId>
      <transitGatewayId>{{ connect.transit_gateway_id }}</transitGatewayId>
      <state>{{ connect.state }}</state>
      <creationTime>{{ connect.creation_time }}</creationTime>
      <options>
        <protocol>{{ connect.options.get('Protocol', 'gre') }}</protocol>
      </options>
      <tagSet>
        {% for tag in connect.get_tags() %}
        <item>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
        {% endfor %}
      </tagSet>
    </item>
    {% endfor %}
  </transitGatewayConnectSet>
</DescribeTransitGatewayConnectsResponse>"""


CREATE_TRANSIT_GATEWAY_CONNECT_PEER = """<CreateTransitGatewayConnectPeerResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnectPeer>
    <transitGatewayConnectPeerId>{{ peer.id }}</transitGatewayConnectPeerId>
    <transitGatewayAttachmentId>{{ peer.transit_gateway_attachment_id }}</transitGatewayAttachmentId>
    <state>{{ peer.state }}</state>
    <creationTime>{{ peer.creation_time }}</creationTime>
    <connectPeerConfiguration>
      <transitGatewayAddress>{{ peer.transit_gateway_address }}</transitGatewayAddress>
      <peerAddress>{{ peer.peer_address }}</peerAddress>
      <insideCidrBlocks>
        {% for cidr in peer.inside_cidr_blocks %}
        <item>{{ cidr }}</item>
        {% endfor %}
      </insideCidrBlocks>
      <protocol>gre</protocol>
      <bgpConfigurations>
        <item>
          <transitGatewayAddress>{{ peer.transit_gateway_address }}</transitGatewayAddress>
          <peerAddress>{{ peer.peer_address }}</peerAddress>
          <peerAsn>{{ peer.bgp_options.get('PeerAsn', '65000') }}</peerAsn>
          <bgpStatus>up</bgpStatus>
        </item>
      </bgpConfigurations>
    </connectPeerConfiguration>
    <tagSet>
      {% for tag in peer.get_tags() %}
      <item>
        <key>{{ tag.key }}</key>
        <value>{{ tag.value }}</value>
      </item>
      {% endfor %}
    </tagSet>
  </transitGatewayConnectPeer>
</CreateTransitGatewayConnectPeerResponse>"""


DELETE_TRANSIT_GATEWAY_CONNECT_PEER = """<DeleteTransitGatewayConnectPeerResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnectPeer>
    <transitGatewayConnectPeerId>{{ peer.id }}</transitGatewayConnectPeerId>
    <state>{{ peer.state }}</state>
  </transitGatewayConnectPeer>
</DeleteTransitGatewayConnectPeerResponse>"""


DESCRIBE_TRANSIT_GATEWAY_CONNECT_PEERS = """<DescribeTransitGatewayConnectPeersResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayConnectPeerSet>
    {% for peer in peers %}
    <item>
      <transitGatewayConnectPeerId>{{ peer.id }}</transitGatewayConnectPeerId>
      <transitGatewayAttachmentId>{{ peer.transit_gateway_attachment_id }}</transitGatewayAttachmentId>
      <state>{{ peer.state }}</state>
      <creationTime>{{ peer.creation_time }}</creationTime>
      <connectPeerConfiguration>
        <transitGatewayAddress>{{ peer.transit_gateway_address }}</transitGatewayAddress>
        <peerAddress>{{ peer.peer_address }}</peerAddress>
        <insideCidrBlocks>
          {% for cidr in peer.inside_cidr_blocks %}
          <item>{{ cidr }}</item>
          {% endfor %}
        </insideCidrBlocks>
        <protocol>gre</protocol>
      </connectPeerConfiguration>
      <tagSet>
        {% for tag in peer.get_tags() %}
        <item>
          <key>{{ tag.key }}</key>
          <value>{{ tag.value }}</value>
        </item>
        {% endfor %}
      </tagSet>
    </item>
    {% endfor %}
  </transitGatewayConnectPeerSet>
</DescribeTransitGatewayConnectPeersResponse>"""


CREATE_TGW_PREFIX_LIST_REFERENCE = """<CreateTransitGatewayPrefixListReferenceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayPrefixListReference>
    <prefixListId>{{ ref.get('prefixListId', '') }}</prefixListId>
    <transitGatewayRouteTableId>{{ ref.get('transitGatewayRouteTableId', '') }}</transitGatewayRouteTableId>
    <state>{{ ref.get('state', 'available') }}</state>
    <blackhole>{{ 'true' if ref.get('blackhole') else 'false' }}</blackhole>
    {% if ref.get('transitGatewayAttachment') %}
    <transitGatewayAttachment>
      <transitGatewayAttachmentId>{{ ref['transitGatewayAttachment']['transitGatewayAttachmentId'] }}</transitGatewayAttachmentId>
      <resourceType>{{ ref['transitGatewayAttachment']['resourceType'] }}</resourceType>
      <resourceId>{{ ref['transitGatewayAttachment']['resourceId'] }}</resourceId>
    </transitGatewayAttachment>
    {% endif %}
  </transitGatewayPrefixListReference>
</CreateTransitGatewayPrefixListReferenceResponse>"""


DELETE_TGW_PREFIX_LIST_REFERENCE = """<DeleteTransitGatewayPrefixListReferenceResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayPrefixListReference>
    <prefixListId>{{ ref.get('prefixListId', '') }}</prefixListId>
    <state>{{ ref.get('state', 'deleted') }}</state>
  </transitGatewayPrefixListReference>
</DeleteTransitGatewayPrefixListReferenceResponse>"""


GET_TGW_PREFIX_LIST_REFERENCES = """<GetTransitGatewayPrefixListReferencesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
  <requestId>7a62c49f-347e-4fc4-9331-6e8eEXAMPLE</requestId>
  <transitGatewayPrefixListReferenceSet>
    {% for ref in refs %}
    <item>
      <prefixListId>{{ ref.get('prefixListId', '') }}</prefixListId>
      <transitGatewayRouteTableId>{{ ref.get('transitGatewayRouteTableId', '') }}</transitGatewayRouteTableId>
      <state>{{ ref.get('state', 'available') }}</state>
      <blackhole>{{ 'true' if ref.get('blackhole') else 'false' }}</blackhole>
      {% if ref.get('transitGatewayAttachment') %}
      <transitGatewayAttachment>
        <transitGatewayAttachmentId>{{ ref['transitGatewayAttachment']['transitGatewayAttachmentId'] }}</transitGatewayAttachmentId>
        <resourceType>{{ ref['transitGatewayAttachment']['resourceType'] }}</resourceType>
        <resourceId>{{ ref['transitGatewayAttachment']['resourceId'] }}</resourceId>
      </transitGatewayAttachment>
      {% endif %}
    </item>
    {% endfor %}
  </transitGatewayPrefixListReferenceSet>
</GetTransitGatewayPrefixListReferencesResponse>"""
