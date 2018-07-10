from __future__ import unicode_literals
import sure  # noqa
import json

import moto.server as server

'''
Test the different server responses
'''


def test_list_apis():
    backend = server.create_backend_app('apigateway')
    test_client = backend.test_client()

    res = test_client.get('/restapis')
    res.data.should.equal(b'{"item": []}')

def test_usage_plans_apis():
    backend = server.create_backend_app('apigateway')
    test_client = backend.test_client()

    '''
    List usage plans (expect empty)
    '''
    res = test_client.get('/usageplans')
    json.loads(res.data)["item"].should.have.length_of(0)

    '''
    Create usage plan
    '''
    res = test_client.post('/usageplans', data=json.dumps({'name': 'test'}))
    created_plan = json.loads(res.data)
    created_plan['name'].should.equal('test')

    '''
    List usage plans (expect 1 plan)
    '''
    res = test_client.get('/usageplans')
    json.loads(res.data)["item"].should.have.length_of(1)

    '''
    Get single usage plan
    '''
    res = test_client.get('/usageplans/{0}'.format(created_plan["id"]))
    fetched_plan = json.loads(res.data)
    fetched_plan.should.equal(created_plan)

    '''
    Delete usage plan
    '''
    res = test_client.delete('/usageplans/{0}'.format(created_plan["id"]))
    res.data.should.equal(b'{}')

    '''
    List usage plans (expect empty again)
    '''
    res = test_client.get('/usageplans')
    json.loads(res.data)["item"].should.have.length_of(0)
