#!/usr/bin/env bash

source ../venv/bin/activate

set -a
source ./manager.env
set +a

if [[ ! ${SOCKET_ADDRESS} ]]
then
	echo "SOCKET_ADDRESS not defined, falling back to default (0.0.0.0)"
	export SOCKET_ADDRESS=0.0.0.0
fi

if [[ ! ${INTERNAL_MANAGEMENT_PORT} ]]
then
	echo "INTERNAL_MANAGEMENT_PORT not defined, falling back to default (8088)"
	export INTERNAL_MANAGEMENT_PORT=8088
fi

if [[ ! ${DJANGO_SUPERUSER_USERNAME} ]]
then
	echo "DJANGO_SUPERUSER_USERNAME not defined, falling back to default (admin)"
	export DJANGO_SUPERUSER_USERNAME=admin
fi

if [[ ! ${DJANGO_SUPERUSER_EMAIL} ]]
then
	echo "DJANGO_SUPERUSER_EMAIL not defined, falling back to default (admin@admin.com)"
	export DJANGO_SUPERUSER_EMAIL=admin@admin.com
fi

if [[ ! ${DJANGO_SUPERUSER_PASSWORD} ]]
then
	echo "DJANGO_SUPERUSER_PASSWORD not defined, falling back to default (password)"
	export DJANGO_SUPERUSER_PASSWORD=password
fi

python3 ./manage.py makemigrations && \
python3 ./manage.py migrate && \
python3 ./manage.py createsuperuser --username ${DJANGO_SUPERUSER_USERNAME} --noinput --email "${DJANGO_SUPERUSER_EMAIL}"
python3 ./manage.py runserver ${SOCKET_ADDRESS}:${INTERNAL_MANAGEMENT_PORT}