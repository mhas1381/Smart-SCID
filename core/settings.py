import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============ SECURITY ============
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

# ============ INSTALLED APPS ============
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party packages
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',  # Swagger/OpenAPI
    
    # Local apps
    'accounts',
    'core',
    'diagnosis',
    'interview',
    'patients',
    'interview_sessions',
]

# ============ MIDDLEWARE ============
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

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

WSGI_APPLICATION = 'core.wsgi.application'

# ============ DATABASE (SQLite) ============
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============ AUTHENTICATION ============
AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============ INTERNATIONALIZATION ============
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# ============ STATIC & MEDIA FILES ============
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'static'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ============ LOGGING CONFIGURATION ============
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    
    # Formatters - define log message format
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'standard': {
            'format': '[{asctime}] [{levelname}] [{name}] - {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} - {message}',
            'style': '{',
        },
    },
    
    # Handlers - define where logs go
    'handlers': {
        # Console output
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'standard',
        },
        # File output - general logs
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'filename': BASE_DIR / 'logs' / 'smart_scid.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # File output - error logs
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        # File output - authentication logs
        'auth_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'filename': BASE_DIR / 'logs' / 'auth.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 3,
            'formatter': 'standard',
        },
        # File output - database logs
        'db_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'filename': BASE_DIR / 'logs' / 'database.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
    },
    
    # Loggers - define which components log
    'loggers': {
        # Root logger - catches everything
        '': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        # Django core
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django requests
        'django.request': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Django database
        'django.db.backends': {
            'handlers': ['db_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Authentication
        'django.security': {
            'handlers': ['auth_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        # Custom app - accounts
        'accounts': {
            'handlers': ['console', 'file', 'auth_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom app - interview
        'interview': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom app - diagnosis
        'diagnosis': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom app - patients
        'patients': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # Custom app - sessions
        'sessions': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ==================== SMS Configuration ====================

# SMS.ir Configuration (for production)
SMS_IR_API_KEY = "your-sms-ir-api-key-here"  # Replace with real key in production
SMS_IR_VERIFY_TEMPLATE_ID = 100000  # Your template ID from SMS.ir

# SMS Mock Mode - Set to True to use mock SMS (logs OTP in console)
# In development, this will be automatically enabled if DEBUG=True
SMS_MOCK_MODE = True  # Force mock mode

# OTP Configuration
OTP_CACHE_TIMEOUT = 120  # 2 minutes - OTP validity period
OTP_LENGTH = 5  # Length of OTP code



# ============ REST FRAMEWORK ============
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ============ JWT SETTINGS ============
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============ CORS SETTINGS ============
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ============ SPECTACULAR (Swagger) SETTINGS ============
SPECTACULAR_SETTINGS = {
    'TITLE': 'Smart SCID API',
    'DESCRIPTION': 'Structured Clinical Interview for DSM-5 Disorders - Digital Version',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/',
    'COMPONENT_SPLIT_REQUEST': True,
    
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    
    'SECURITY': [
        {'Bearer': []},
    ],
    
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'description': 'Enter JWT token with Bearer prefix (e.g. Bearer <token>)',
        }
    },
}