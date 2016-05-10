from moto.core.responses import BaseResponse
from .models import moto_backends

import json
from functools import partial
from datetime import datetime
from moto.backends import BACKENDS

from six.moves.urllib.parse import parse_qs, urlparse


class attr_or_itemgetter(object):
    # A very convenient mix between the best of operator.itemgetter and
    # operator.attrgetter: support nested attributes or items, attributes
    # preferred, .-separated
    def __init__(self, *specs):
        self.__specs__ = specs

    def __get_attr_or_item__(self, obj, spec):
        current = obj
        for path_elem in spec.split('.'):
            if hasattr(current, path_elem):
                current = getattr(current, path_elem)
                continue
            current = current[path_elem]
        return current

    def __call__(self, obj):
        result = tuple(
            self.__get_attr_or_item__(obj, part)
            for part in self.__specs__
        )
        return result


def evaluator(target, method_path, params):
    method_path = method_path.replace('/', '.')
    leaf = attr_or_itemgetter(method_path)(target)[0]
    assert(callable(leaf) or (not params))
    if not callable(leaf):
        return leaf
    print params
    return leaf(**params)


def dump_pod(done_set, obj):
    if isinstance(obj, datetime):
        return obj.isoformat()+'+00:00'

    result = dict(
        (a, getattr(obj, a)) for a in dir(obj)
        if (not a.startswith('_')
            and not a.endswith('_backend'))
        and not callable(getattr(obj, a))
        and not id(getattr(obj,a)) in done_set
    )
    done_set.add(id(obj))
    return result


class MotoResponse(BaseResponse):
    @classmethod
    def dynamic_invoke(cls, request, full_url, headers):
        if request.method == 'PUT':
            return cls()._dynamic_invoke_put(request, full_url, headers)
        else:
            raise ValueError("Cannot handle request")

    def _dynamic_invoke_put(self, request, full_url, headers):
        parsed_url = urlparse(full_url)

        if hasattr(request, 'body'):
            # Boto
            body = request.body
        else:
            # Flask server
            body = request.data
        body = body.decode('utf-8')

        args = json.loads(body.decode('utf-8'))
        result = evaluator(BACKENDS, parsed_url.path[len('/rpc/reflect/'):], args)
        result_pod = json.dumps(result, default=partial(dump_pod, set()))
        return 200, headers, result_pod
