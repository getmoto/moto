#!/usr/bin/env bash
set -e
pip install $(ls /moto/dist/moto*.gz)[server,all]
moto_server -H 0.0.0.0 -p 5000
