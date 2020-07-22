from __future__ import unicode_literals

from ..core.models import BaseMockAWS, MOTO_NONO_ATTR


class NoNoBackend(BaseMockAWS):
    def decorate_class(self, klass):
        raise NotImplementedError()

    def decorate_callable(self, func, reset):
        wrapped = super(NoNoBackend, self).decorate_callable(func, reset)
        setattr(wrapped, MOTO_NONO_ATTR, True)
        return wrapped

    def start(self, reset=True):
        pass

    def stop(self):
        pass


class nono_decorator(object):
    mock_backend = NoNoBackend

    def __init__(self):
        pass

    def __call__(self, func=None):
        mocked_backend = self.mock_backend(backends={})

        if func:
            return mocked_backend(func)
        else:
            return mocked_backend


mock_nono_moto = nono_decorator()
