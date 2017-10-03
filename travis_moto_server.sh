#!/usr/bin/env bash
set -e
pip install /moto/dist/moto*.gz[server,lambda]
moto_server -H 0.0.0.0 -p 5000