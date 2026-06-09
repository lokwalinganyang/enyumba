import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-nyumba@2026')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['.vercel.app', 'localhost', '127.0.0.1']

# ---------- VERCEL‑SPECIFIC SETTINGS (CSRF, SESSIONS, COOKIES) ----------
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://enyumba.vercel.app',
]
SESSION_COOKIE_DOMAIN = '.vercel.app'
CSRF_COOKIE_DOMAIN = '.vercel.app'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False        # Required for JavaScript to read cookie (if any)
SESSION_COOKIE_SAMESITE = 'None'    # Allows cross‑subdomain cookies
CSRF_COOKIE_SAMESITE = 'None'
CSRF_REFERER_POLICY = 'unsafe-url'  # Allows missing Referer header (common on Vercel)
# -----------------------------------------------------------------------

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

# ---------- DATABASE (Always use DATABASE_URL from Vercel environment) ----------
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://user:pass@localhost:5432/db',   # fallback (not used on Vercel)
        conn_max_age=600,
        ssl_require=True
    )
}

# ---------- STATIC & MEDIA ----------
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# ---------- AUTH & RATE LIMITING ----------
LOGIN_URL = '/admin/login/'
CONTACT_REVEAL_LIMIT = 5
CONTACT_REVEAL_WINDOW = 86400   # 24h