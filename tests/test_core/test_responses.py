from __future__ import unicode_literals

import sure  # noqa

from moto.core.responses import flatten_json_request_body


def test_flatten_json_request_body():
    jd = {'A': {'B': 1,
                'C': [2, 3],
                'D': [{'E': True, 'F': False},
                      {'E': None, 'F': 7}],
                'G': [{'H': [{'I': 'good', 'J': 'bad'}]}]}}
    flat = flatten_json_request_body(jd)
    flat['A.B'].should.equal('1')
    flat['A.C.member.1'].should.equal('2')
    flat['A.C.member.2'].should.equal('3')
    flat['A.D.member.1.E'].should.equal('true')
    flat['A.D.member.1.F'].should.equal('false')
    flat['A.D.member.2.E'].should.equal('null')
    flat['A.D.member.2.F'].should.equal('7')
    flat['A.G.member.1.H.member.1.I'].should.equal('good')
    flat['A.G.member.1.H.member.1.J'].should.equal('bad')
