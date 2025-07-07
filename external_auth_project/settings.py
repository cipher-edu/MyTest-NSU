from pathlib import Path
import logging
logger = logging.getLogger(__name__)
import environ
import os

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1','*'])

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_results',
    'auth_app',
    'rest_framework',
    'rest_framework_simplejwt',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
STATIC_URL = '/static/' 
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_DIR = BASE_DIR / 'media'
MEDIA_ROOT = MEDIA_DIR
MEDIA_URL = '/media/'
X_FRAME_OPTIONS = 'DENY' 
CSRF_COOKIE_HTTPONLY = True  
CSRF_COOKIE_AGE = 60 * 60 * 24  
CSRF_COOKIE_PATH = '/'  
CSRF_COOKIE_DOMAIN = None  
CSRF_COOKIE_NAME = 'hemis_csrf_token'  
CSRF_USE_SESSIONS = False  
CSRF_COOKIE_SECURE = True  
CSRF_COOKIE_SAMESITE = 'Lax' 
ROOT_URLCONF = 'external_auth_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  
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

CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env('REDIS_URL', default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

EXTERNAL_API_BASE_URL = env('EXTERNAL_API_BASE_URL', default="https://student.nspi.uz/rest")
EXTERNAL_API_LOGIN_ENDPOINT = f"{EXTERNAL_API_BASE_URL}/v1/auth/login"
EXTERNAL_API_ACCOUNT_ME_ENDPOINT = f"{EXTERNAL_API_BASE_URL}/v1/account/me"
EXTERNAL_API_REFRESH_TOKEN_ENDPOINT = f"{EXTERNAL_API_BASE_URL}/v1/auth/refresh-token" 
REQUESTS_VERIFY_SSL = env.bool('REQUESTS_VERIFY_SSL', default=True)

API_TOKEN_REFRESH_THRESHOLD_SECONDS = 10 * 60 

HEMIS_ADMIN_API_TOKEN = env('b1scfqAQKK2PjRvll0MTAbFOQ1yumi4b', default=None) 
HEMIS_SYSTEM_API_TOKEN = env('HEMIS_SYSTEM_API_TOKEN', default=None)

EXTERNAL_API_LOGOUT_ENDPOINT = env('EXTERNAL_API_LOGOUT_ENDPOINT', default=None) 

WSGI_APPLICATION = 'external_auth_project.wsgi.application'
# settings.py

LOGIN_URL = 'auth_app:login'  
LOGIN_REDIRECT_URL = 'auth_app:dashboard' # Odatda 'home' yoki 'dashboard' bo'ladi
LOGOUT_REDIRECT_URL = 'auth_app:login' # Chiqishdan keyin qayerga yo'naltirish

DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME', default='survey_prod_db'),
        'USER': env('DB_USER', default='survey_user'),
        'PASSWORD': env('DB_PASSWORD', default='super_secret_password'),
        'HOST': env('DB_HOST', default='db'),
        'PORT': env('DB_PORT', default='5432'),
    }
}


if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default'].pop('USER', None)
    DATABASES['default'].pop('PASSWORD', None)
    DATABASES['default'].pop('HOST', None)
    DATABASES['default'].pop('PORT', None)
elif DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
    DATABASES['default'].setdefault('OPTIONS', {
        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        'charset': 'utf8mb4', 
    })
    if DATABASES['default'].get('PORT'):
        try:
            DATABASES['default']['PORT'] = int(DATABASES['default']['PORT'])
        except ValueError:
            logger.warning(f"DB_PORT qiymati ({DATABASES['default']['PORT']}) raqam emas. MySQL uchun standart port ishlatiladi yoki xatolik yuz berishi mumkin.")
            DATABASES['default']['PORT'] = '3306' 

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

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

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Tashkent'

USE_I18N = True

USE_TZ = True

TEST_IP_CHECK_ENABLED = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_AGE = 24 * 60 * 60  

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'django_app.log',
            'maxBytes': 1024*1024*5,
            'backupCount': 2,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'auth_app': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'requests': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    }
}