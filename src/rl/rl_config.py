"""
Configuration management for the Flask application.
Handles different environments and deployment scenarios.
"""
import os
import secrets
from dotenv import load_dotenv
from datetime import timedelta

class Config:
    """Base configuration class with common settings."""
    # Default settings, these values are overridden by environment variables for deployment
    SECRET_KEY = os.environ.get('SECRET_KEY',b' q/\x8ax"\xe9\xfc\x8a0v\x1a\x18\r\x8f\xc1\xb7\xf4\x14\xd0\xb8j:\xb1') 
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin')
    
    # Security settings (common to all configurations)
    SESSION_COOKIE_NAME = 'session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # Critical fix: Set the session cookie domain to match both localhost and IP access
    # When None, Flask automatically uses the domain from the request
    SESSION_COOKIE_DOMAIN = None  
    # Ensure consistent session ID between requests
    SESSION_USE_SIGNER = True
    # Set session type
    SESSION_TYPE = 'filesystem'
    # Make sessions permanent with a reasonable timeout
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    # Fix for server name used in redirects and cookies
    SERVER_NAME  = None  # Let Flask handle this automatically

    @staticmethod
    def init_app(app):
        """Initialize the application with this configuration."""
        pass


class DevelopmentConfig(Config):
    """Development environment configuration."""
    FLASK_ENV = 'development'
    FLASK_DEBUG = True
    DEBUG = True
    PORT = int(os.environ.get('PORT', 5000))
    SESSION_COOKIE_SECURE = False
    FLASK_RUN_RELOAD = True
    WTF_CSRF_ENABLED = False     # Enable CSRF protection, change to True in production
    WTF_CSRF_SSL_STRICT = False # Require HTTPS for CSRF requests, change to True in production
    USE_DOCKER = True # default value may get overwritten in get_config

class ProductionConfig(Config):
    """Production environment configuration."""
    FLASK_ENV = 'production'
    FLASK_DEBUG = False
    DEBUG = False
    PORT = int(os.environ.get('PORT', 8080))  # Always default to 8080 for production
    SESSION_COOKIE_SECURE = False  # Set to True when using HTTPS
    FLASK_RUN_RELOAD = False
    WTF_CSRF_ENABLED = False     # Enable CSRF protection, change to True in production
    WTF_CSRF_SSL_STRICT = False # Require HTTPS for CSRF requests, change to True in production
    USE_DOCKER = True # default value may get overwritten in get_config

class DeployConfig(Config):
    """Production environment configuration."""
    FLASK_ENV = 'production'
    FLASK_DEBUG = False
    DEBUG = False
    PORT = int(os.environ.get('PORT', 8080))  # Always default to 8080 for production
    SESSION_COOKIE_SECURE = True              # Set to True when using HTTPS
    FLASK_RUN_RELOAD = True
    WTF_CSRF_ENABLED = True                   # Enable CSRF protection, change to True in production
    WTF_CSRF_SSL_STRICT = True                # Require HTTPS for CSRF requests, change to True in production
    USE_DOCKER = True

# Configuration dictionary mapping environment names to config classes
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'deploy': DeployConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the appropriate configuration based on environment variables."""
    env_mode = os.environ.get('ENV_MODE', 'development').lower()
    
    # Load the appropriate .env file
    if env_mode == 'production':
        load_dotenv('.env.production')
    elif env_mode == 'deploy':
        load_dotenv('.env.deploy')
    else:
        load_dotenv('.env.development')      

    #just  loaded from .env file.
    use_docker = os.environ.get('USE_DOCKER', 'False')

    # Get the configuration class
    config_class = config.get(env_mode, config['default'])

    #save for future use....
    config_class.USE_DOCKER = use_docker
    
    print(f"ENV_MODE: {env_mode}")
    print(f"USE_DOCKER: {use_docker}")
    
    return config_class