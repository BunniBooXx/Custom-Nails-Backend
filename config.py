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

    # Mail settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS")
    MAILJET_API_KEY= os.environ.get("MAILJET_API_KEY")
    MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER=os.environ.get("MAILJET_FROM_EMAIL")
    DEVELOPER_EMAIL = os.environ.get("DEVELOPER_EMAIL")
    TOKEN_URI= os.environ.get('TOKEN_URI')

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    CLIENT_EMAIL= os.getenv('CLIENT_EMAIL')



    SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
  

    # JWT
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
