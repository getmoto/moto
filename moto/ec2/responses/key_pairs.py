from jinja2 import Template
from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend


class KeyPairs(BaseResponse):

    def create_key_pair(self):
        name = self.querystring.get('KeyName')[0]
        template = Template(CREATE_KEY_PAIR_RESPONSE)
        return template.render(**ec2_backend.create_key_pair(name))

    def delete_key_pair(self):
        raise NotImplementedError('KeyPairs.delete_key_pair is not yet implemented')

    def describe_key_pairs(self):
        template = Template(DESCRIBE_KEY_PAIRS_RESPONSE)
        return template.render(keypairs=ec2_backend.describe_key_pairs())

    def import_key_pair(self):
        raise NotImplementedError('KeyPairs.import_key_pair is not yet implemented')


DESCRIBE_KEY_PAIRS_RESPONSE = """<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId> 
    <keySet>
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
