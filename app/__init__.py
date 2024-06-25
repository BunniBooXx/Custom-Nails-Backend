import os
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import logging
from logging.handlers import RotatingFileHandler
from email.mime.text import MIMEText
from flask_session import Session
from app.models import User, Order, db
import base64

app = Flask(__name__, template_folder='templates', static_url_path='/nails', static_folder='nails')
app.config.from_object(os.getenv('APP_SETTINGS'))

print(f"Using configuration: {os.getenv('APP_SETTINGS')}")

mail = Mail(app)
jwt = JWTManager(app)

CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://nail-shop.onrender.com"]}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")


# Set up logging
if not app.debug:
    handler = RotatingFileHandler('error.log', maxBytes=10000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
else:
    logging.basicConfig(level=logging.DEBUG)

# Ensure a secret key is set for session management
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

from app.order.routes import order_blueprint
from app.user.routes import user_blueprint
from app.product.routes import product_blueprint
from app.cart.routes import cart_blueprint 

app.register_blueprint(user_blueprint, url_prefix='/user')
app.register_blueprint(product_blueprint, url_prefix='/product')
app.register_blueprint(order_blueprint, url_prefix='/order')
app.register_blueprint(cart_blueprint, url_prefix='/cart')

# Flask-Session setup
app.config['SESSION_TYPE'] = 'filesystem'  # Use filesystem for simplicity, change to Redis or other for production
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'flask-session:'
app.config['SESSION_FILE_DIR'] = '/tmp/flask-session/'  # Ensure this directory exists and is writable

# Create session directory if it does not exist
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])
    print(f"Created session directory: {app.config['SESSION_FILE_DIR']}")
else:
    print(f"Session directory exists: {app.config['SESSION_FILE_DIR']}")

Session(app)

db.init_app(app)


SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'config', 'client_secrets.json')
print(f"CLIENT_SECRETS_FILE path: {CLIENT_SECRETS_FILE}")

if not os.path.exists(CLIENT_SECRETS_FILE):
    raise FileNotFoundError(f"Client secrets file not found at path: {CLIENT_SECRETS_FILE}")

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2_callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    print(f"State set in session: {state}")  # Debug statement
    return redirect(authorization_url)

@app.route('/oauth2/callback')
def oauth2_callback():
    state = session.get('state')
    if not state:
        return jsonify({'error': 'State not found in session'}), 400

    print(f"State retrieved from session: {state}")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2_callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    session['credentials'] = credentials_to_dict(credentials)
    print("Credentials stored in session:", session['credentials'])
    return redirect(url_for('send_email'))


def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_gmail_service():
    try:
        if 'credentials' not in session:
            raise ValueError("No credentials found in session")
        credentials_dict = session['credentials']
        app.logger.debug(f"Credentials found in session: {credentials_dict}")
        
        credentials = Credentials(**credentials_dict)
        return build('gmail', 'v1', credentials=credentials)
    except ValueError as e:
        app.logger.error(f"ValueError: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Exception in get_gmail_service: {str(e)}")
        return None


import os

@app.route('/send-email', methods=['POST'])
@jwt_required()
def send_email():
    current_user_id = get_jwt_identity()
    app.logger.info(f"Current User ID: {current_user_id}")

    if not request.is_json:
        return jsonify({'error': 'Unsupported Media Type. Expected application/json.'}), 415

    data = request.get_json()

    if not data or not all(key in data for key in ['recipient', 'subject', 'body']):
        return jsonify({'error': 'Missing recipient, subject, or body in request body'}), 400

    recipient = data['recipient']
    subject = data['subject']
    body = data['body']

    try:
        service = get_gmail_service()
        if not service:
            raise Exception("Gmail service not initialized")

        message = create_message(recipient, subject, body)
        send_message(service, 'me', message)

        return jsonify({'message': 'Email sent successfully'}), 200
    except Exception as e:
        app.logger.error(f"Failed to send email. Error: {str(e)}")
        return jsonify({'error': f'Failed to send email. Error: {str(e)}'}), 500

def create_message(recipient, subject, body):
    message = MIMEText(body, 'html')
    message['to'] = recipient
    message['subject'] = subject
    raw_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    return raw_message

def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId=user_id, body=message).execute()
        print('Message Id: %s' % message['id'])
        return message
    except Exception as error:
        print('An error occurred: %s' % error)
        raise

app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
print(f"JWT Secret Key: {app.config['JWT_SECRET_KEY']}")

@app.route('/debug-token', methods=['GET'])
@jwt_required()
def debug_token():
    current_user_id = get_jwt_identity()
    return jsonify({"current_user_id": current_user_id}), 200



@app.route('/')
def index():
    return 'Welcome to your Flask application!'

if __name__ == '__main__':
    port = int(os.getenv('PORT', 1000))
    app.run(host='0.0.0.0', port=port)












