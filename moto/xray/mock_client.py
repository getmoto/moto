from functools import wraps
import os
from moto.xray import xray_backends
import aws_xray_sdk.core
from aws_xray_sdk.core.context import Context as AWSContext
from aws_xray_sdk.core.emitters.udp_emitter import UDPEmitter


class MockEmitter(UDPEmitter):
    """
    Replaces the code that sends UDP to local X-Ray daemon
    """
    def __init__(self, daemon_address='127.0.0.1:2000'):
        address = os.getenv('AWS_XRAY_DAEMON_ADDRESS_YEAH_NOT_TODAY_MATE', daemon_address)
        self._ip, self._port = self._parse_address(address)

    def _xray_backend(self, region):
        return xray_backends[region]

    def send_entity(self, entity):
        # Hack to get region
        # region = entity.subsegments[0].aws['region']
        # xray = self._xray_backend(region)

        # TODO store X-Ray data, pretty sure X-Ray needs refactor for this
        pass

    def _send_data(self, data):
        raise RuntimeError('Should not be running this')


def mock_xray_client(f):
    """
    Mocks the X-Ray sdk by pwning its evil singleton with our methods

    The X-Ray SDK has normally been imported and `patched()` called long before we start mocking.
    This means the Context() will be very unhappy if an env var isnt present, so we set that, save
    the old context, then supply our new context.
    We also patch the Emitter by subclassing the UDPEmitter class replacing its methods and pushing
    that itno the recorder instance.
    """
    @wraps(f)
    def _wrapped(*args, **kwargs):
        print("Starting X-Ray Patch")

        old_xray_context_var = os.environ.get('AWS_XRAY_CONTEXT_MISSING')
        os.environ['AWS_XRAY_CONTEXT_MISSING'] = 'LOG_ERROR'
        old_xray_context = aws_xray_sdk.core.xray_recorder._context
        old_xray_emitter = aws_xray_sdk.core.xray_recorder._emitter
        aws_xray_sdk.core.xray_recorder._context = AWSContext()
        aws_xray_sdk.core.xray_recorder._emitter = MockEmitter()

        try:
            return f(*args, **kwargs)
        finally:

            if old_xray_context_var is None:
                del os.environ['AWS_XRAY_CONTEXT_MISSING']
            else:
                os.environ['AWS_XRAY_CONTEXT_MISSING'] = old_xray_context_var

            aws_xray_sdk.core.xray_recorder._emitter = old_xray_emitter
            aws_xray_sdk.core.xray_recorder._context = old_xray_context

    return _wrapped


class XRaySegment(object):
    """
    XRay is request oriented, when a request comes in, normally middleware like django (or automatically in lambda) will mark
    the start of a segment, this stay open during the lifetime of the request. During that time subsegments may be generated
    by calling other SDK aware services or using some boto functions. Once the request is finished, middleware will also stop
    the segment, thus causing it to be emitted via UDP.

    During testing we're going to have to control the start and end of a segment via context managers.
    """
    def __enter__(self):
        aws_xray_sdk.core.xray_recorder.begin_segment(name='moto_mock', traceid=None, parent_id=None, sampling=1)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        aws_xray_sdk.core.xray_recorder.end_segment()
