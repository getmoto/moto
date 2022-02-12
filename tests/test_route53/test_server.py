import sure  # noqa # pylint: disable=unused-import
import xmltodict

import moto.server as server


def test_list_recordset():
    backend = server.create_backend_app("route53")
    test_client = backend.test_client()

    # create hosted zone
    request_data = '<CreateHostedZoneRequest xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><Name>example.com</Name><CallerReference>2014-04-01-18:47</CallerReference></CreateHostedZoneRequest>'
    res = test_client.post("2013-04-01/hostedzone", data=request_data)
    body = parse_xml(res.data)
    zone_id = body["CreateHostedZoneResponse"]["HostedZone"]["Id"].rsplit("/")[-1]

    # change record set
    # Contains a special character
    request_data = '<ChangeResourceRecordSetsRequest xmlns="https://route53.amazonaws.com/doc/2013-04-01/"><ChangeBatch><Changes><Change><Action>CREATE</Action><ResourceRecordSet><Name>n.example.com</Name><Type>TXT</Type><SetIdentifier>string</SetIdentifier><Weight>1</Weight><Region>us-east-1</Region><ResourceRecords><ResourceRecord><Value>val&amp;sth</Value></ResourceRecord></ResourceRecords></ResourceRecordSet></Change></Changes></ChangeBatch></ChangeResourceRecordSetsRequest>'
    test_client.post(f"2013-04-01/hostedzone/{zone_id}/rrset/", data=request_data)

    # list record set
    res = test_client.get(f"2013-04-01/hostedzone/{zone_id}/rrset")
    # Ampersand should be properly encoded
    res.data.decode("utf-8").should.contain("<Value><![CDATA[val&sth]]></Value>")


def parse_xml(body):
    return xmltodict.parse(body, dict_constructor=dict)
