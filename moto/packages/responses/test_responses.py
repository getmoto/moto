from __future__ import (
    absolute_import, print_function, division, unicode_literals
)

import re
import requests
import responses
import pytest

from inspect import getargspec
from requests.exceptions import ConnectionError, HTTPError


def assert_reset():
    assert len(responses._default_mock._urls) == 0
    assert len(responses.calls) == 0


def assert_response(resp, body=None, content_type='text/plain'):
    assert resp.status_code == 200
    assert resp.reason == 'OK'
    if content_type is not None:
        assert resp.headers['Content-Type'] == content_type
    else:
        assert 'Content-Type' not in resp.headers
    assert resp.text == body


def test_response():
    @responses.activate
    def run():
        responses.add(responses.GET, 'http://example.com', body=b'test')
        resp = requests.get('http://example.com')
        assert_response(resp, 'test')
        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'http://example.com/'
        assert responses.calls[0].response.content == b'test'

        resp = requests.get('http://example.com?foo=bar')
        assert_response(resp, 'test')
        assert len(responses.calls) == 2
        assert responses.calls[1].request.url == 'http://example.com/?foo=bar'
        assert responses.calls[1].response.content == b'test'

    run()
    assert_reset()


def test_connection_error():
    @responses.activate
    def run():
        responses.add(responses.GET, 'http://example.com')

        with pytest.raises(ConnectionError):
            requests.get('http://example.com/foo')

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'http://example.com/foo'
        assert type(responses.calls[0].response) is ConnectionError
        assert responses.calls[0].response.request

    run()
    assert_reset()


def test_match_querystring():
    @responses.activate
    def run():
        url = 'http://example.com?test=1&foo=bar'
        responses.add(
            responses.GET, url,
            match_querystring=True, body=b'test')
        resp = requests.get('http://example.com?test=1&foo=bar')
        assert_response(resp, 'test')
        resp = requests.get('http://example.com?foo=bar&test=1')
        assert_response(resp, 'test')

    run()
    assert_reset()


def test_match_querystring_error():
    @responses.activate
    def run():
        responses.add(
            responses.GET, 'http://example.com/?test=1',
            match_querystring=True)

        with pytest.raises(ConnectionError):
            requests.get('http://example.com/foo/?test=2')

    run()
    assert_reset()


def test_match_querystring_regex():
    @responses.activate
    def run():
        """Note that `match_querystring` value shouldn't matter when passing a
        regular expression"""

        responses.add(
            responses.GET, re.compile(r'http://example\.com/foo/\?test=1'),
            body='test1', match_querystring=True)

        resp = requests.get('http://example.com/foo/?test=1')
        assert_response(resp, 'test1')

        responses.add(
            responses.GET, re.compile(r'http://example\.com/foo/\?test=2'),
            body='test2', match_querystring=False)

        resp = requests.get('http://example.com/foo/?test=2')
        assert_response(resp, 'test2')

    run()
    assert_reset()


def test_match_querystring_error_regex():
    @responses.activate
    def run():
        """Note that `match_querystring` value shouldn't matter when passing a
        regular expression"""

        responses.add(
            responses.GET, re.compile(r'http://example\.com/foo/\?test=1'),
            match_querystring=True)

        with pytest.raises(ConnectionError):
            requests.get('http://example.com/foo/?test=3')

        responses.add(
            responses.GET, re.compile(r'http://example\.com/foo/\?test=2'),
            match_querystring=False)

        with pytest.raises(ConnectionError):
            requests.get('http://example.com/foo/?test=4')

    run()
    assert_reset()


def test_accept_string_body():
    @responses.activate
    def run():
        url = 'http://example.com/'
        responses.add(
            responses.GET, url, body='test')
        resp = requests.get(url)
        assert_response(resp, 'test')

    run()
    assert_reset()


def test_accept_json_body():
    @responses.activate
    def run():
        content_type = 'application/json'

        url = 'http://example.com/'
        responses.add(
            responses.GET, url, json={"message": "success"})
        resp = requests.get(url)
        assert_response(resp, '{"message": "success"}', content_type)

        url = 'http://example.com/1/'
        responses.add(responses.GET, url, json=[])
        resp = requests.get(url)
        assert_response(resp, '[]', content_type)

    run()
    assert_reset()


def test_no_content_type():
    @responses.activate
    def run():
        url = 'http://example.com/'
        responses.add(
            responses.GET, url, body='test', content_type=None)
        resp = requests.get(url)
        assert_response(resp, 'test', content_type=None)

    run()
    assert_reset()


def test_throw_connection_error_explicit():
    @responses.activate
    def run():
        url = 'http://example.com'
        exception = HTTPError('HTTP Error')
        responses.add(
            responses.GET, url, exception)

        with pytest.raises(HTTPError) as HE:
            requests.get(url)

        assert str(HE.value) == 'HTTP Error'

    run()
    assert_reset()


def test_callback():
    body = b'test callback'
    status = 400
    reason = 'Bad Request'
    headers = {'foo': 'bar'}
    url = 'http://example.com/'

    def request_callback(request):
        return (status, headers, body)

    @responses.activate
    def run():
        responses.add_callback(responses.GET, url, request_callback)
        resp = requests.get(url)
        assert resp.text == "test callback"
        assert resp.status_code == status
        assert resp.reason == reason
        assert 'foo' in resp.headers
        assert resp.headers['foo'] == 'bar'

    run()
    assert_reset()


def test_callback_no_content_type():
    body = b'test callback'
    status = 400
    reason = 'Bad Request'
    headers = {'foo': 'bar'}
    url = 'http://example.com/'

    def request_callback(request):
        return (status, headers, body)

    @responses.activate
    def run():
        responses.add_callback(
            responses.GET, url, request_callback, content_type=None)
        resp = requests.get(url)
        assert resp.text == "test callback"
        assert resp.status_code == status
        assert resp.reason == reason
        assert 'foo' in resp.headers
        assert 'Content-Type' not in resp.headers

    run()
    assert_reset()


def test_regular_expression_url():
    @responses.activate
    def run():
        url = re.compile(r'https?://(.*\.)?example.com')
        responses.add(responses.GET, url, body=b'test')

        resp = requests.get('http://example.com')
        assert_response(resp, 'test')

        resp = requests.get('https://example.com')
        assert_response(resp, 'test')

        resp = requests.get('https://uk.example.com')
        assert_response(resp, 'test')

        with pytest.raises(ConnectionError):
            requests.get('https://uk.exaaample.com')

    run()
    assert_reset()


def test_custom_adapter():
    @responses.activate
    def run():
        url = "http://example.com"
        responses.add(responses.GET, url, body=b'test')

        calls = [0]

        class DummyAdapter(requests.adapters.HTTPAdapter):

            def send(self, *a, **k):
                calls[0] += 1
                return super(DummyAdapter, self).send(*a, **k)

        # Test that the adapter is actually used
        session = requests.Session()
        session.mount("http://", DummyAdapter())

        resp = session.get(url, allow_redirects=False)
        assert calls[0] == 1

        # Test that the response is still correctly emulated
        session = requests.Session()
        session.mount("http://", DummyAdapter())

        resp = session.get(url)
        assert_response(resp, 'test')

    run()


def test_responses_as_context_manager():
    def run():
        with responses.mock:
            responses.add(responses.GET, 'http://example.com', body=b'test')
            resp = requests.get('http://example.com')
            assert_response(resp, 'test')
            assert len(responses.calls) == 1
            assert responses.calls[0].request.url == 'http://example.com/'
            assert responses.calls[0].response.content == b'test'

            resp = requests.get('http://example.com?foo=bar')
            assert_response(resp, 'test')
            assert len(responses.calls) == 2
            assert (responses.calls[1].request.url ==
                    'http://example.com/?foo=bar')
            assert responses.calls[1].response.content == b'test'

    run()
    assert_reset()


def test_activate_doesnt_change_signature():
    def test_function(a, b=None):
        return (a, b)

    decorated_test_function = responses.activate(test_function)
    assert getargspec(test_function) == getargspec(decorated_test_function)
    assert decorated_test_function(1, 2) == test_function(1, 2)
    assert decorated_test_function(3) == test_function(3)


def test_activate_doesnt_change_signature_for_method():
    class TestCase(object):

        def test_function(self, a, b=None):
            return (self, a, b)

    test_case = TestCase()
    argspec = getargspec(test_case.test_function)
    decorated_test_function = responses.activate(test_case.test_function)
    assert argspec == getargspec(decorated_test_function)
    assert decorated_test_function(1, 2) == test_case.test_function(1, 2)
    assert decorated_test_function(3) == test_case.test_function(3)


def test_response_cookies():
    body = b'test callback'
    status = 200
    headers = {'set-cookie': 'session_id=12345; a=b; c=d'}
    url = 'http://example.com/'

    def request_callback(request):
        return (status, headers, body)

    @responses.activate
    def run():
        responses.add_callback(responses.GET, url, request_callback)
        resp = requests.get(url)
        assert resp.text == "test callback"
        assert resp.status_code == status
        assert 'session_id' in resp.cookies
        assert resp.cookies['session_id'] == '12345'
        assert resp.cookies['a'] == 'b'
        assert resp.cookies['c'] == 'd'
    run()
    assert_reset()


def test_assert_all_requests_are_fired():
    def run():
        with pytest.raises(AssertionError) as excinfo:
            with responses.RequestsMock(
                    assert_all_requests_are_fired=True) as m:
                m.add(responses.GET, 'http://example.com', body=b'test')
        assert 'http://example.com' in str(excinfo.value)
        assert responses.GET in str(excinfo)

        # check that assert_all_requests_are_fired default to True
        with pytest.raises(AssertionError):
            with responses.RequestsMock() as m:
                m.add(responses.GET, 'http://example.com', body=b'test')

        # check that assert_all_requests_are_fired doesn't swallow exceptions
        with pytest.raises(ValueError):
            with responses.RequestsMock() as m:
                m.add(responses.GET, 'http://example.com', body=b'test')
                raise ValueError()

    run()
    assert_reset()


def test_allow_redirects_samehost():
    redirecting_url = 'http://example.com'
    final_url_path = '/1'
    final_url = '{0}{1}'.format(redirecting_url, final_url_path)
    url_re = re.compile(r'^http://example.com(/)?(\d+)?$')

    def request_callback(request):
        # endpoint of chained redirect
        if request.url.endswith(final_url_path):
            return 200, (), b'test'
        # otherwise redirect to an integer path
        else:
            if request.url.endswith('/0'):
                n = 1
            else:
                n = 0
            redirect_headers = {'location': '/{0!s}'.format(n)}
            return 301, redirect_headers, None

    def run():
        # setup redirect
        with responses.mock:
            responses.add_callback(responses.GET, url_re, request_callback)
            resp_no_redirects = requests.get(redirecting_url,
                                             allow_redirects=False)
            assert resp_no_redirects.status_code == 301
            assert len(responses.calls) == 1  # 1x300
            assert responses.calls[0][1].status_code == 301
        assert_reset()

        with responses.mock:
            responses.add_callback(responses.GET, url_re, request_callback)
            resp_yes_redirects = requests.get(redirecting_url,
                                              allow_redirects=True)
            assert len(responses.calls) == 3  # 2x300 + 1x200
            assert len(resp_yes_redirects.history) == 2
            assert resp_yes_redirects.status_code == 200
            assert final_url == resp_yes_redirects.url
            status_codes = [call[1].status_code for call in responses.calls]
            assert status_codes == [301, 301, 200]
        assert_reset()

    run()
    assert_reset()
