"""
Django settings for whatisit project.

Generated by 'django-admin startproject' using Django 1.9.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DOMAIN_NAME = "https://word.fish"
DOMAIN_NAME_HTTP = "http://whatisit.org"
ADMINS = (('vsochat', 'vsochat@gmail.com'),)
MANAGERS = ADMINS

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_user_agents',
    'whatisit.apps.wordfish',
    'whatisit.apps.main',
    'whatisit.apps.api',
    'whatisit.apps.users',
]

THIRD_PARTY_APPS = [
    'social.apps.django_app.default',
    'crispy_forms',
    'opbeat.contrib.django',
    'djcelery',
    'rest_framework',
    'rest_framework.authtoken',
    'guardian',
    'django_gravatar',
    'lockdown',
    'taggit',
]


INSTALLED_APPS += THIRD_PARTY_APPS

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lockdown.middleware.LockdownMiddleware',
]

ROOT_URLCONF = 'whatisit.urls'

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
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
                'whatisit.apps.main.context_processors.domain_processor', #custom context processor
                'whatisit.apps.main.context_processors.disqus_processor', #custom context processor
            ],
        },
    },
]

TEMPLATES[0]['OPTIONS']['debug'] = True
WSGI_APPLICATION = 'whatisit.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': 'db',
        'PORT': '5432',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

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


AUTHENTICATION_BACKENDS = (
    'social.backends.open_id.OpenIdAuth',
    'social.backends.facebook.FacebookOAuth2',
    'social.backends.google.GoogleOAuth2',
    'social.backends.twitter.TwitterOAuth',
    'social.backends.github.GithubOAuth2',
    'django.contrib.auth.backends.ModelBackend', # default
    'guardian.backends.ObjectPermissionBackend',
)

# Python-social-auth

SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'whatisit.apps.users.views.social_user',
    'whatisit.apps.users.views.redirect_if_no_refresh_token',
    'social.pipeline.user.get_username',
    'social.pipeline.social_auth.associate_by_email',  # <--- must share same email
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details',
)


# http://psa.matiasaguirre.net/docs/configuration/settings.html#urls-options
#SOCIAL_AUTH_USER_MODEL = 'django.contrib.auth.models.User'
#SOCIAL_AUTH_STORAGE = 'social.apps.django_app.me.models.DjangoStorage'
#SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/logged-in/'
#SOCIAL_AUTH_LOGIN_ERROR_URL = '/login-error/'
#SOCIAL_AUTH_LOGIN_URL = '/login-url/'
#SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/new-users-redirect-url/'
#SOCIAL_AUTH_LOGIN_REDIRECT_URL
#SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/new-association-redirect-url/'
#SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/account-disconnected-redirect-url/'
#SOCIAL_AUTH_INACTIVE_USER_URL = '/inactive-user/'

# Django Lockdown
LOCKDOWN_ENABLED=True


# Api
API_VERSION = "v1"

REST_FRAMEWORK = {

    #'DEFAULT_PERMISSION_CLASSES': [
    #    'rest_framework.permissions.IsAuthenticated',
    #],
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),

    'PAGE_SIZE': 10
}


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_L10N = True
USE_TZ = True

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

SENDFILE_BACKEND = 'sendfile.backends.development'
PRIVATE_MEDIA_REDIRECT_HEADER = 'X-Accel-Redirect'
CRISPY_TEMPLATE_PACK = 'bootstrap3'

CACHES = {
            'default': {
                'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

MEDIA_ROOT = '/var/www/images'
MEDIA_URL = '/images/'
STATIC_ROOT = '/var/www/static'
STATIC_URL = '/static/'

# CELERY SETTINGS
REDIS_PORT = 6379  
REDIS_DB = 0  
REDIS_HOST = os.environ.get('REDIS_PORT_6379_TCP_ADDR', 'redis')

# CELERY SETTINGS
CELERY_ALWAYS_EAGER = False  
CELERY_ACKS_LATE = True  
CELERY_TASK_PUBLISH_RETRY = True  
CELERY_DISABLE_RATE_LIMITS = False

# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level
CELERY_IGNORE_RESULT = False
CELERY_SEND_TASK_ERROR_EMAILS = False  
CELERY_TASK_RESULT_EXPIRES = 600
CELERY_RESULT_BACKEND = 'redis://%s:%d/%d' %(REDIS_HOST,REDIS_PORT,REDIS_DB)

BROKER_URL = os.environ.get('BROKER_URL',None)
if BROKER_URL == None:
    BROKER_URL = CELERY_RESULT_BACKEND

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ENABLE_UTC = True  
CELERY_TIMEZONE = "UTC"

# Gravatar
GRAVATAR_DEFAULT_IMAGE = "retro" 
DISQUS_NAME = 'wordfish'
# An image url or one of the following: 'mm', 'identicon', 'monsterid', 'wavatar', 'retro'. Defaults to 'mm'

# Report Gold Standard Settings

# The minimum number of annotations required (across reports) to allow
# generation of a set for annotation
GOLD_STANDARD_MIN_ANNOTS=25

# Bogus secret key.
try:
    from whatisit.secrets import *
except ImportError:
    from whatisit.bogus_secrets import *

# Local settings
try:
    from whatisit.local_settings import *
except ImportError:
    pass
