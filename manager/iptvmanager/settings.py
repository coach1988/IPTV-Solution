"""
Django settings for iptvmanager project.

Generated by 'django-admin startproject' using Django 4.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
import logging
import mimetypes

from pathlib import Path

__DEFAULT_DJANGO_SUPERUSER_USERNAME = 'admin'
__DEFAULT_DJANGO_SUPERUSER_EMAIL = 'admin@admin.com'
__DEFAULT_DJANGO_SUPERUSER_PASSWORD = 'password'
__DEFAULT_SOCKET_ADDRESS = '0.0.0.0'
__DEFAULT_INTERNAL_MANAGEMENT_PORT = '8088'
__DEFAULT_EXTERNAL_MANAGEMENT_PORT = '8088'
__DEFAULT_USER_AGENT_STRING = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36)'
__DEFAULT_PLAYLIST_TIMEOUT = 120
__DEFAULT_EPG_TIMEOUT = 120
__DEFAULT_ICON_TIMEOUT = 15
__DEFAULT_INTERNAL_TIMEOUT = 1
__DEFAULT_ALLOWED_HOSTS =  ['*']
__DEFAULT_DEBUG = False

# https://stackoverflow.com/questions/35557129/css-not-loading-wrong-mime-type-django
mimetypes.add_type("text/css", ".css", True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ['DEBUG']) if 'DEBUG' in os.environ else __DEFAULT_DEBUG

ALLOWED_HOSTS = eval(os.environ['ALLOWED_HOSTS']) if 'ALLOWED_HOSTS' in os.environ else __DEFAULT_ALLOWED_HOSTS

# Application definition

INSTALLED_APPS = [
    'manager.apps.ManagerConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iptvmanager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'iptvmanager.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASE_DIR = Path(f'{BASE_DIR}/database')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ['TIME_ZONE'] if 'TIME_ZONE' in os.environ else 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/
STATICFILES_DIRS = [
   os.path.join(BASE_DIR, 'manager/static/')
]

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

###########################################################################################################
#
#	Django settings
#
###########################################################################################################

CSRF_TRUSTED_ORIGINS = [os.environ['MANAGEMENT_URL']]
DJANGO_SUPERUSER_USERNAME = os.environ['DJANGO_SUPERUSER_USERNAME'] if 'DJANGO_SUPERUSER_USERNAME' in os.environ else __DEFAULT_DJANGO_SUPERUSER_USERNAME
DJANGO_SUPERUSER_EMAIL = os.environ['DJANGO_SUPERUSER_EMAIL'] if 'DJANGO_SUPERUSER_EMAIL' in os.environ else __DEFAULT_DJANGO_SUPERUSER_EMAIL
DJANGO_SUPERUSER_PASSWORD = os.environ['DJANGO_SUPERUSER_PASSWORD'] if 'DJANGO_SUPERUSER_PASSWORD' in os.environ else __DEFAULT_DJANGO_SUPERUSER_PASSWORD

SOCKET_ADDRESS = os.environ['SOCKET_ADDRESS'] if 'SOCKET_ADDRESS' in os.environ else __DEFAULT_SOCKET_ADDRESS
MANAGEMENT_URL = os.environ['MANAGEMENT_URL']
INTERNAL_MANAGEMENT_PORT = os.environ['INTERNAL_MANAGEMENT_PORT'] if 'INTERNAL_MANAGEMENT_PORT' in os.environ else __DEFAULT_INTERNAL_MANAGEMENT_PORT
EXTERNAL_MANAGEMENT_PORT = os.environ['EXTERNAL_MANAGEMENT_PORT'] if 'EXTERNAL_MANAGEMENT_PORT' in os.environ else __DEFAULT_EXTERNAL_MANAGEMENT_PORT

USER_AGENT_STRING = os.environ['USER_AGENT_STRING'] if 'USER_AGENT_STRING' in os.environ else __DEFAULT_USER_AGENT_STRING
PLAYLIST_TIMEOUT = int(os.environ['PLAYLIST_TIMEOUT']) if 'PLAYLIST_TIMEOUT' in os.environ else __DEFAULT_PLAYLIST_TIMEOUT
EPG_TIMEOUT = int(os.environ['EPG_TIMEOUT']) if 'EPG_TIMEOUT' in os.environ else __DEFAULT_EPG_TIMEOUT
ICON_TIMEOUT = int(os.environ['ICON_TIMEOUT']) if 'ICON_TIMEOUT' in os.environ else __DEFAULT_ICON_TIMEOUT
INTERNAL_TIMEOUT = int(os.environ['INTERNAL_TIMEOUT']) if 'INTERNAL_TIMEOUT' in os.environ else __DEFAULT_INTERNAL_TIMEOUT

logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Django
logger.info(f'ALLOWED_HOSTS: {ALLOWED_HOSTS}')
logger.info(f'TIME_ZONE: {TIME_ZONE}')
logger.info(f'DJANGO_SUPERUSER_USERNAME: {DJANGO_SUPERUSER_USERNAME}')
logger.info(f'DJANGO_SUPERUSER_EMAIL: {DJANGO_SUPERUSER_EMAIL}')
logger.info(f'DJANGO_SUPERUSER_PASSWORD: {DJANGO_SUPERUSER_PASSWORD}')
logger.info(f'SECRET_KEY: {SECRET_KEY}')
logger.info(f'DEBUG: {DEBUG}')

# Network
logger.info(f'SOCKET_ADDRESS: {SOCKET_ADDRESS}')
logger.info(f'MANAGEMENT_URL: {MANAGEMENT_URL}')
logger.info(f'INTERNAL_MANAGEMENT_PORT: {INTERNAL_MANAGEMENT_PORT}')
logger.info(f'EXTERNAL_MANAGEMENT_PORT: {EXTERNAL_MANAGEMENT_PORT}')
logger.info(f'INTERNAL_TIMEOUT: {INTERNAL_TIMEOUT}')

# Upstream connection
logger.info(f'USER_AGENT_STRING: {USER_AGENT_STRING}')
logger.info(f'PLAYLIST_TIMEOUT: {PLAYLIST_TIMEOUT}')
logger.info(f'EPG_TIMEOUT: {EPG_TIMEOUT}')
logger.info(f'ICON_TIMEOUT: {ICON_TIMEOUT}')

# Misc
logger.info(f'DATABASE_DIR: {DATABASE_DIR}')
logger.info(f'CSRF_TRUSTED_ORIGINS: {CSRF_TRUSTED_ORIGINS}')