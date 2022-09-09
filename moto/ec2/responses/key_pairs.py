from ._base_response import EC2BaseResponse


class KeyPairs(EC2BaseResponse):
    def create_key_pair(self):
        name = self._get_param("KeyName")
        if self.is_not_dryrun("CreateKeyPair"):
            keypair = self.ec2_backend.create_key_pair(name)
            template = self.response_template(CREATE_KEY_PAIR_RESPONSE)
            return template.render(keypair=keypair)

    def delete_key_pair(self):
        name = self._get_param("KeyName")
        if self.is_not_dryrun("DeleteKeyPair"):
            success = str(self.ec2_backend.delete_key_pair(name)).lower()
            return self.response_template(DELETE_KEY_PAIR_RESPONSE).render(
                success=success
            )

    def describe_key_pairs(self):
        names = self._get_multi_param("KeyName")
        filters = self._filters_from_querystring()
        keypairs = self.ec2_backend.describe_key_pairs(names, filters)
        template = self.response_template(DESCRIBE_KEY_PAIRS_RESPONSE)
        return template.render(keypairs=keypairs)

    def import_key_pair(self):
        name = self._get_param("KeyName")
        material = self._get_param("PublicKeyMaterial")
        if self.is_not_dryrun("ImportKeyPair"):
            keypair = self.ec2_backend.import_key_pair(name, material)
            template = self.response_template(IMPORT_KEYPAIR_RESPONSE)
            return template.render(keypair=keypair)


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
   <keyName>{{ keypair.name }}</keyName>
   <keyFingerprint>{{ keypair.fingerprint }}</keyFingerprint>
   <keyMaterial>{{ keypair.material }}</keyMaterial>
</CreateKeyPairResponse>"""


DELETE_KEY_PAIR_RESPONSE = """<DeleteKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
  <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId>
  <return>{{ success }}</return>
</DeleteKeyPairResponse>"""

IMPORT_KEYPAIR_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
  <ImportKeyPairResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>471f9fdd-8fe2-4a84-86b0-bd3d3e350979</requestId>
    <keyName>{{ keypair.name }}</keyName>
    <keyFingerprint>{{ keypair.fingerprint }}</keyFingerprint>
  </ImportKeyPairResponse>"""
