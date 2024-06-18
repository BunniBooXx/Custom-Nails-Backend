from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from app.models import User, Order, db
import base64
import os

app = Flask(__name__, template_folder='templates', static_url_path='/nails', static_folder='nails')
app.config.from_object(os.getenv('APP_SETTINGS'))  # Ensure APP_SETTINGS points to your config file
mail = Mail(app)
jwt = JWTManager(app)

# Update CORS configuration to include both localhost and hosted frontend
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://nail-shop.onrender.com"]}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db.init_app(app)

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CLIENT_SECRETS_FILE = os.getenv('CLIENT_SECRETS_FILE')

if not os.path.exists(CLIENT_SECRETS_FILE):
    raise FileNotFoundError(f"Client secrets file not found at path: {CLIENT_SECRETS_FILE}")

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2_callback', _external=True)  # Ensure this matches the URI in Google Cloud Console
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2/callback')
def oauth2_callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2_callback', _external=True)  # Ensure this matches the URI in Google Cloud Console
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials

    session['credentials'] = credentials_to_dict(credentials)
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
    if 'credentials' not in session:
        raise ValueError("No credentials in session")
    
    credentials = Credentials(**session['credentials'])
    return build('gmail', 'v1', credentials=credentials)

@app.route('/send-email', methods=['POST'])
@jwt_required()
def send_email():
    current_user_id = get_jwt_identity()

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

        message = create_message(recipient, subject, body)
        send_message(service, 'me', message)

        return jsonify({'message': 'Email sent successfully'}), 200
    
    except Exception as e:
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

@app.route('/')
def index():
    return 'Welcome to your Flask application!'

if __name__ == '__main__':
    app.run(port=5000, debug=True)

