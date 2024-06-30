import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FLASK_APP = os.environ.get("FLASK_APP")
    FLASK_DEBUG = os.environ.get("FLASK_DEBUG")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # FLASK JWT EXTENDED
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_TOKEN_LOCATION = ['headers']

    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")

    DEVELOPER_EMAIL = os.environ.get("DEVELOPER_EMAIL")


    TOKEN_URI = os.environ.get('TOKEN_URI')
    MAIL_SERVER= 'smtp.gmail.com'
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USE_SSL=False
    MAIL_USERNAME = 'bunnybubblenails@gmail.com'
    MAIL_PASSWORD= 'tuff cgft rbad cfmx'
    MAIL_DEFAULT_SENDER='bunnybubblenails@gmail.com'

    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    CLIENT_SECRETS_FILE = os.environ.get('CLIENT_SECRETS_FILE')
    CLIENT_EMAIL = os.environ.get('CLIENT_EMAIL')
    APP_SETTINGS = os.environ.get('APP_SETTINGS')

    SERVICE_ACCOUNT_FILE = os.environ.get('SERVICE_ACCOUNT_FILE')

    # Add a secret key for Flask session management
    FLASK_SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')

