#!/usr/bin/env bash
travis_retry pip install boto==2.45.0
travis_retry pip install boto3
travis_retry pip install .
travis_retry pip install -r requirements-dev.txt