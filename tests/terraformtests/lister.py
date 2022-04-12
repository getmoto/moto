import inspect
import logging
import os
import subprocess
import threading
from collections import defaultdict

logger = logging.getLogger(__name__)

root_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), ''))
list_bin = os.path.join(root_dir, 'bin/list-tests')


def list_tests(query, list_all=False):
    cwd = os.getcwd()
    os.chdir(root_dir)
    try:
        cmd = [list_bin]
        if list_all:
            cmd.append('--all')
        cmd.append(f'{query}')
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        return proc.stdout.splitlines()
    finally:
        os.chdir(cwd)


def collect(suite=None):
    _load_caches()
    if suite is None:
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        filename = module.__file__
        suite = os.path.basename(filename)[:-3]  # /path/to/TestAccAWSSQSQueue.py -> TestAccAWSSQSQueue

    return _cache_suites[suite]


_cache_loaded = threading.Event()
_cache_suites = {}
_cache_tests = []


def _load_caches():
    global _cache_loaded, _cache_suites, _cache_tests
    if _cache_loaded.is_set():
        return
    _cache_loaded.set()

    pattern = os.path.join(root_dir, 'terraform-provider-aws/internal/service/**/*_test.go')
    logger.info('locating go test suites in %s', pattern)
    cmd = f'grep "^func TestAcc" {pattern}'
    lines = subprocess.check_output(cmd, shell=True, text=True).splitlines(keepends=False)
    logger.info('found %d records', len(lines))

    suite_tests = defaultdict(list)

    for line in lines:
        if not line:
            continue

        path, signature = line.split(':', maxsplit=1)
        test = signature[5:].split('(')[0]  # func TestAccAWSXray_foo(t *testing.T) { -> TestAccAWSXray_foo
        suite = test.split('_')[0]
        service_name = path.split('internal/service/')[1].split('/')[0]
        test_ref = f"{service_name}:{test}"
        suite_tests[suite].append(test_ref)
        _cache_tests.append(test_ref)

    _cache_suites = suite_tests