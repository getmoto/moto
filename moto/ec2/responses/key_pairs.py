from jinja2 import Template
from moto.core.responses import BaseResponse


class KeyPairs(BaseResponse):
    def create_key_pair(self):
        raise NotImplementedError('KeyPairs.create_key_pair is not yet implemented')

    def delete_key_pair(self):
        raise NotImplementedError('KeyPairs.delete_key_pair is not yet implemented')

    def describe_key_pairs(self):
        template = Template(DESCRIBE_KEY_PAIRS_RESPONSE)
        return template.render(keypairs=[])

    def import_key_pair(self):
        raise NotImplementedError('KeyPairs.import_key_pair is not yet implemented')


DESCRIBE_KEY_PAIRS_RESPONSE = """<DescribeKeyPairsResponse xmlns="http://ec2.amazonaws.com/doc/2013-10-15/">
    <requestId>59dbff89-35bd-4eac-99ed-be587EXAMPLE</requestId> 
    <keySet>
    </keySet>
 </DescribeKeyPairsResponse>"""
