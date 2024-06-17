from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from email.mime.text import MIMEText
from app.models import User, Order,db
import base64
import os

app = Flask(__name__, template_folder='templates', static_url_path='/nails', static_folder='nails')
app.config.from_object(os.getenv('APP_SETTINGS'))  # Ensure APP_SETTINGS points to your config file
mail = Mail(app)
jwt = JWTManager(app)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

db.init_app(app) 
# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
DEVELOPER_EMAIL = os.getenv('DEVELOPER_EMAIL')

def get_gmail_service():
    flow = InstalledAppFlow.from_client_secrets_file(SERVICE_ACCOUNT_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

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
