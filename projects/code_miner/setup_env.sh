#!/usr/bin/env bash

ENV_NAME=miner_env

python3 -m venv $ENV_NAME
$ENV_NAME/bin/pip install --upgrade pip
$ENV_NAME/bin/pip install -r requirements.txt

echo "Environment ready: $ENV_NAME"
