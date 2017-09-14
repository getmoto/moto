#!/usr/bin/env bash
set -e
cd /moto

travis_retry() {
    "$@"
}

source /moto/travis_install.sh
moto_server -H 0.0.0.0 -p 5000