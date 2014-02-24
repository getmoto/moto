from jinja2 import Template
from moto.core.responses import BaseResponse
from moto.ec2.models import ec2_backend
from moto.ec2.exceptions import InvalidIdError


class KeyPairs(BaseResponse):

    def create_key_pair(self):
        try:
            name = self.querystring.get('KeyName')[0]
            keypair = ec2_backend.create_key_pair(name)
        except InvalidIdError as exc:
            template = Template(CREATE_KEY_PAIR_INVALID_NAME)
            return template.render(keypair_id=exc.id), dict(status=400)
        else:
            template = Template(CREATE_KEY_PAIR_RESPONSE)
            return template.render(**keypair)

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


CREATE_KEY_PAIR_INVALID_NAME = """<?xml version="1.0" encoding="UTF-8"?>
<Response><Errors><Error><Code>InvalidKeyPair.Duplicate</Code><Message>The keypair '{{ keypair_id }}' already exists.</Message></Error></Errors><RequestID>f4f76e81-8ca5-4e61-a6d5-a4a96EXAMPLE</RequestID></Response>
"""
