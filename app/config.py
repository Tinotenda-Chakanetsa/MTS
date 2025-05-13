import os
from datetime import timedelta

class Config:
    # Basic Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    DEBUG = False
    TESTING = False
    
    # PostgreSQL Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:root@localhost:5432/mtspro'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session Config
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Mail Config
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.example.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # App Constants
    ITEMS_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Security
    PASSWORD_HASH_METHOD = 'pbkdf2:sha256:100000'
    TOKEN_EXPIRATION = 3600  # 1 hour

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:root@localhost:5432/mtspro_test'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    # Production specific settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

# Dictionary to easily access different configs
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}