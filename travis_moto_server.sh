#!/usr/bin/env bash
set -e

travis_retry() {
    "$@"
}

pip install /moto/dist/moto*.gz
pip install flask
moto_server -H 0.0.0.0 -p 5000