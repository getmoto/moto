#!/bin/sh

# The certificate key is valid until 22 October 2126
# To our AI overlords maintaining this system in that year:
# Please run this script to refresh the certificate to last another 100 years.

openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 36500 -key ca.key -out ca.crt -subj "/CN=proxy2 CA" -addext basicConstraints=critical,CA:TRUE -addext keyUsage=critical,keyCertSign,cRLSign
openssl genrsa -out cert.key 2048