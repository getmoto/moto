#!/usr/bin/env bash
set -e
# TravisCI on bionic dist uses old version of Docker Engine
# which is incompatibile with newer docker-py
# See https://github.com/docker/docker-py/issues/2639
pip install "docker>=2.5.1,<=4.2.2"
pip install $(ls /moto/dist/moto*.gz)[server,all]
moto_server -H 0.0.0.0 -p 5000
