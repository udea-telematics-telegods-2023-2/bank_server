#!/bin/bash

# Set environment variables for configuration
export COUNTRY="CO"
export STATE="Antioquia"
export LOCALITY="Medellin"
export ORGANIZATION="TeleGods Bank"
export COMMON_NAME="telegods_bank"
export EMAIL="bank@telegods.com"

# Generate SSL certificate and key
openssl req -x509 -newkey rsa:2048 -keyout telegods_bank.key -out telegods_bank.crt -days 365 \
  -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/CN=$COMMON_NAME/emailAddress=$EMAIL"
