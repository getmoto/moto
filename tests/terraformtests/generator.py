import os

from .lister import list_tests

template = """import pytest
from .lister import collect
from .runner import assert_test
tests = collect('{suite}')
@pytest.mark.parametrize('test_name', tests)
def test(test_name):
    assert_test(test_name)
"""

aws_tests_dir = os.path.join(os.path.dirname(__file__))


def generate_aws():
    os.makedirs(aws_tests_dir, exist_ok=True)

    tests = list_tests('TestAcc')
    init_file = os.path.join(aws_tests_dir, '__init__.py')
    if not os.path.isfile(init_file):
        with open(init_file, 'w') as fd:
            fd.write(os.linesep)

    for test in tests:
        test_file = os.path.join(aws_tests_dir, f'{test}.py')

        if os.path.isfile(test_file):
            continue

        print('creating', test_file)
        with open(test_file, 'w') as fd:
            fd.write(template.format(suite=os.path.basename(test_file)[:-3]))


def main():
    generate_aws()


if __name__ == '__main__':
    main()