#!/usr/bin/env bash

source ../venv/bin/activate

set -a
source ./manager.env
set +a

python3 ./manage.py ${1}
