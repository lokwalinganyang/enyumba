import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-fallback')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'   # set to True temporarily

ALLOWED_HOSTS = ['.vercel.app', 'localhost', '127.0.0.1']

# ---------- CRITICAL COOKIE SETTINGS FOR VERCEL ----------
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://enyumba.vercel.app',
]
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_DOMAIN = '.vercel.app'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_DOMAIN = '.vercel.app'
# ---------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'enyumba',
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

ROOT_URLCONF = 'config.urls'

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
                'enyumba.context_processors.ads_context',
            ],
        },
    },
]

# Database
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://user:pass@localhost:5432/db',
        conn_max_age=600,
        ssl_require=True
    )
}

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('duhyohtyq'),
    'API_KEY': os.environ.get('996447835644153'),
    'API_SECRET': os.environ.get('8MFrFHGH1MVr2uC_OTo_xBaEwVI'),
}

LOGIN_URL = '/admin/login/'
CONTACT_REVEAL_LIMIT = 5
CONTACT_REVEAL_WINDOW = 86400