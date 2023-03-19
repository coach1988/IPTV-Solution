#!/usr/bin/env bash

source ../venv/bin/activate

set -a
source ./proxy.env
set +a

python3 ./proxy.py
