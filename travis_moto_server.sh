#!/usr/bin/env bash

export MOTO_PORT=${MOTO_PORT:-5000}

set -e
pip install $(ls /moto/dist/moto*.gz)[server,all]
moto_server -H 0.0.0.0 -p ${MOTO_PORT} > /moto/server_output.log 2>&1
