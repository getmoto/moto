#
# Dependency Integration Test script
#

# Runs a test to verify whether each service has the correct dependencies listed in setup.py
#
# Tests that depend on multiple services are assumed to be located in dedicated testfiles (and ignored during this test)
# (test_*_integration.py/test_*_cloudformation.py)
#
# ::Algorithm::
# For each valid service:
#   - Create a virtual environment
#   - Install only the necessary dependencies
#   - Run the tests for that service
#   - If the tests fail:
#     - This service is probably missing a dependency
#     - A log file with the test results will be created (test_results_service.log)
#   - Delete the virtual environment
#
# Note:
#   Only tested on Linux
#   Parallelized to test 4 services at the time.
#   Could take some time to run - around 20 minutes on the author's machine


overwrite() { echo -e "\r\033[1A\033[0K$@"; }

contains() {
    [[ $1 =~ (^|[[:space:]])$2($|[[:space:]]) ]] && return 0 || return 1
}

valid_service() {
  # Verify whether this is a valid service
  # We'll ignore metadata folders, and folders that test generic Moto behaviour
  # We'll also ignore CloudFormation, as it will always depend on other services
  local ignore_moto_folders="core instance_metadata __pycache__ templates cloudformation moto_api moto_server packages utilities s3bucket_path"
  if echo $ignore_moto_folders | grep -q "$1"; then
    return 1
  else
    return 0
  fi
}

test_service() {
  service=$1
  path_to_test_file=$2
  venv_path="test_venv_${service}"
  overwrite "Running tests for ${service}.."
  python -m venv ${venv_path}
  source ${venv_path}/bin/activate
  pip install --upgrade pip setuptools
  # Can't just install requirements-file, as it points to all dependencies
  pip install -r requirements-tests.txt
  pip install .[$service]
  pip install boto
  if [[ $service != "xray" ]]; then
    pip uninstall setuptools pkg_resources -y
  fi
  # Restart venv - ensure these deps are loaded
  deactivate
  source ${venv_path}/bin/activate
  # Run tests for this service
  pytest -sv --ignore-glob="**/test_server.py" --ignore-glob="**/test_*_cloudformation.py" --ignore-glob="**/test_*_integration.py" $path_to_test_file
  RESULT=$?
  deactivate
  rm -rf ${venv_path}
  if [[ $RESULT != 0 ]]; then
    echo -e "Tests for ${service} have failed!\n"
    exit -1
  fi
}

service=$1
if [[ $# -eq 0 ]] ; then
    echo 'Please add the name of the service you want to test as the first argument:'
    echo '    scripts/dependency_test.sh acm'
    exit 0
fi
echo "Running Dependency tests for {$1}..."
path_to_test_file="tests/test_${service}"
if valid_service $service && [[ -d $path_to_test_file ]]; then
  test_service $service $path_to_test_file
  if [[ $? != 0 ]]; then
    exit -1
  fi
elif valid_service $service; then
  echo -e "No tests for ${service} can be found on ${path_to_test_file}!\n"
fi
