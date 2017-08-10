Responses
=========

.. image:: https://travis-ci.org/getsentry/responses.svg?branch=master
	:target: https://travis-ci.org/getsentry/responses

A utility library for mocking out the `requests` Python library.

.. note:: Responses requires Requests >= 2.0

Response body as string
-----------------------

.. code-block:: python

    import responses
    import requests

    @responses.activate
    def test_my_api():
        responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
                      body='{"error": "not found"}', status=404,
                      content_type='application/json')

        resp = requests.get('http://twitter.com/api/1/foobar')

        assert resp.json() == {"error": "not found"}

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'http://twitter.com/api/1/foobar'
        assert responses.calls[0].response.text == '{"error": "not found"}'

You can also specify a JSON object instead of a body string.

.. code-block:: python

    import responses
    import requests

    @responses.activate
    def test_my_api():
        responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
                      json={"error": "not found"}, status=404)

        resp = requests.get('http://twitter.com/api/1/foobar')

        assert resp.json() == {"error": "not found"}

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'http://twitter.com/api/1/foobar'
        assert responses.calls[0].response.text == '{"error": "not found"}'

Request callback
----------------

.. code-block:: python

    import json

    import responses
    import requests

    @responses.activate
    def test_calc_api():

        def request_callback(request):
            payload = json.loads(request.body)
            resp_body = {'value': sum(payload['numbers'])}
            headers = {'request-id': '728d329e-0e86-11e4-a748-0c84dc037c13'}
            return (200, headers, json.dumps(resp_body))

        responses.add_callback(
            responses.POST, 'http://calc.com/sum',
            callback=request_callback,
            content_type='application/json',
        )

        resp = requests.post(
            'http://calc.com/sum',
            json.dumps({'numbers': [1, 2, 3]}),
            headers={'content-type': 'application/json'},
        )

        assert resp.json() == {'value': 6}

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'http://calc.com/sum'
        assert responses.calls[0].response.text == '{"value": 6}'
        assert (
            responses.calls[0].response.headers['request-id'] ==
            '728d329e-0e86-11e4-a748-0c84dc037c13'
        )

Instead of passing a string URL into `responses.add` or `responses.add_callback`
you can also supply a compiled regular expression.

.. code-block:: python

    import re
    import responses
    import requests

    # Instead of
    responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
                  body='{"error": "not found"}', status=404,
                  content_type='application/json')

    # You can do the following
    url_re = re.compile(r'https?://twitter\.com/api/\d+/foobar')
    responses.add(responses.GET, url_re,
                  body='{"error": "not found"}', status=404,
                  content_type='application/json')

A response can also throw an exception as follows.

.. code-block:: python

    import responses
    import requests
    from requests.exceptions import HTTPError

    exception = HTTPError('Something went wrong')
    responses.add(responses.GET, 'http://twitter.com/api/1/foobar',
                  body=exception)
    # All calls to 'http://twitter.com/api/1/foobar' will throw exception.


Responses as a context manager
------------------------------

.. code-block:: python

    import responses
    import requests


    def test_my_api():
        with responses.RequestsMock() as rsps:
            rsps.add(responses.GET, 'http://twitter.com/api/1/foobar',
                     body='{}', status=200,
                     content_type='application/json')
            resp = requests.get('http://twitter.com/api/1/foobar')

            assert resp.status_code == 200

        # outside the context manager requests will hit the remote server
        resp = requests.get('http://twitter.com/api/1/foobar')
        resp.status_code == 404


Assertions on declared responses
--------------------------------

When used as a context manager, Responses will, by default, raise an assertion
error if a url was registered but not accessed. This can be disabled by passing
the ``assert_all_requests_are_fired`` value:

.. code-block:: python

    import responses
    import requests


    def test_my_api():
        with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
            rsps.add(responses.GET, 'http://twitter.com/api/1/foobar',
                     body='{}', status=200,
                     content_type='application/json')

Multiple Responses
------------------
You can also use ``assert_all_requests_are_fired`` to add multiple responses for the same url:

.. code-block:: python

    import responses
    import requests


    def test_my_api():
        with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
            rsps.add(responses.GET, 'http://twitter.com/api/1/foobar', status=500)
            rsps.add(responses.GET, 'http://twitter.com/api/1/foobar',
                     body='{}', status=200,
                     content_type='application/json')

            resp = requests.get('http://twitter.com/api/1/foobar')
            assert resp.status_code == 500
            resp = requests.get('http://twitter.com/api/1/foobar')
            assert resp.status_code == 200
