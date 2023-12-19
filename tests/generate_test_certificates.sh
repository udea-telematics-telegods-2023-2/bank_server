#!/bin/bash

# Set environment variables for configuration
export COUNTRY="CO"
export STATE="Antioquia"
export LOCALITY="Medellin"
export ORGANIZATION="TeleGods Bank"
export COMMON_NAME="localhost"
export EMAIL="bank@telegods.com"

# Generate SSL certificate and key without passphrase
openssl req -x509 -newkey rsa:2048 -keyout test.key -out test.crt -days 365 \
  -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/CN=$COMMON_NAME/emailAddress=$EMAIL" \
  -nodes
