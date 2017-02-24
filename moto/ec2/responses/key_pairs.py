from __future__ import unicode_literals
import six
from moto.core.responses import BaseResponse
from moto.ec2.utils import keypair_names_from_querystring, filters_from_querystring


class KeyPairs(BaseResponse):

    def create_key_pair(self):
        name = self.querystring.get('KeyName')[0]
        if self.is_not_dryrun('CreateKeyPair'):
            keypair = self.ec2_backend.create_key_pair(name)
            template = self.response_template(CREATE_KEY_PAIR_RESPONSE)
            return template.render(**keypair)

    def delete_key_pair(self):
        name = self.querystring.get('KeyName')[0]
        if self.is_not_dryrun('DeleteKeyPair'):
            success = six.text_type(
                self.ec2_backend.delete_key_pair(name)).lower()
            return self.response_template(DELETE_KEY_PAIR_RESPONSE).render(success=success)

    def describe_key_pairs(self):
        names = keypair_names_from_querystring(self.querystring)
        filters = filters_from_querystring(self.querystring)
        if len(filters) > 0:
            raise NotImplementedError(
                'Using filters in KeyPairs.describe_key_pairs is not yet implemented')

        keypairs = self.ec2_backend.describe_key_pairs(names)
        template = self.response_template(DESCRIBE_KEY_PAIRS_RESPONSE)
        return template.render(keypairs=keypairs)

    def import_key_pair(self):
        name = self.querystring.get('KeyName')[0]
        material = self.querystring.get('PublicKeyMaterial')[0]
        if self.is_not_dryrun('ImportKeyPair'):
            keypair = self.ec2_backend.import_key_pair(name, material)
            template = self.response_template(IMPORT_KEYPAIR_RESPONSE)
            return template.render(**keypair)


DESCRIBE_KEY_PAIRS_RESPONSE = """<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
    <keySet>
    {% for keypair in keypairs %}
      <item>
           <keyName>{{ keypair.name }}</keyName>
           <keyFingerprint>{{ keypair.fingerprint }}</keyFingerprint>
      </item>
    {% endfor %}
    </keySet>
 </DescribeKeyPairsResponse>"""


CREATE_KEY_PAIR_RESPONSE = """<CreateKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
   <keyName>{{ name }}</keyName>
   <keyFingerprint>
        {{ fingerprint }}
   </keyFingerprint>
   <keyMaterial>{{ material }}
    </keyMaterial>
</CreateKeyPairResponse>"""


DELETE_KEY_PAIR_RESPONSE = """<DeleteKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeleteKeyPairResponse>"""

IMPORT_KEYPAIR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
  <ImportKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>471f9fdd-8fe2-4a84-86b0-bd3d3e350979</requestId>
    <keyName>{{ name }}</keyName>
    <keyFingerprint>{{ fingerprint }}</keyFingerprint>
  </ImportKeyPairResponse>"""
