try:
    from collections import OrderedDict  # flake8: noqa
except ImportError:
    # python 2.6 or earlier, use backport
    from ordereddict import OrderedDict  # flake8: noqa

# AWS Lambda support is optional
try:
    import docker
    SUPPORTS_LAMBDA = True
except ImportError:
    SUPPORTS_LAMBDA = False
