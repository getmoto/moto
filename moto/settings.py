import os

TEST_SERVER_MODE = os.environ.get('TEST_SERVER_MODE', '0').lower() == 'true'
SERVER_HOSTNAME = 'moto_server' if TEST_SERVER_MODE else 'localhost'
SERVER_BASE_URL = 'http://{}:5000'.format(SERVER_HOSTNAME)
