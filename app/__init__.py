import os
from flask import Flask, request, jsonify, redirect, url_for, session, render_template
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
from app.models import User, Order, db, OrderItem
import base64

app = Flask(__name__, template_folder='templates', static_url_path='/nails', static_folder='nails')

# Additional configuration for hosted environment
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config.from_object(os.getenv('APP_SETTINGS'))


# Configure logging
logging.basicConfig(level=logging.INFO)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Internal Server Error: {error}')
    return jsonify({'error': 'Internal Server Error', 'message': str(error)}), 500

@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        app.logger.info(f"Fetching user with ID: {user_id}")
        user = User.query.get(user_id)
        if user:
            return jsonify(user.to_response())
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        app.logger.error(f'Error fetching user: {e}')
        return jsonify({'error': 'Failed to fetch user', 'message': str(e)}), 500



mail = Mail(app)
jwt = JWTManager(app)
from flask_migrate import Migrate


migrate = Migrate(app, db)

CORS(app, resources={r"/*": {"origins": ["https://localhost:3000", "https://nail-shop.onrender.com"]}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

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
        ##if 'credentials' not in session:
          ##  raise ValueError("No credentials found in session")
       ## credentials_dict = session['credentials']
        ##app.logger.debug(f"Credentials found in session: {credentials_dict}")
        
       ## credentials = Credentials(**credentials_dict)
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file('app/config/nail-shop.json')
        return build('gmail', 'v1', credentials=credentials)
    except ValueError as e:
        app.logger.error(f"ValueError: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Exception in get_gmail_service: {str(e)}")
        return None


import os


    


@app.route('/send-emails', methods=['POST'])
@jwt_required()
def send_emails():
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    if not request.is_json:
        return jsonify({'message': 'Request payload must be in JSON format'}), 400

    data = request.get_json()
    user_id = data.get('user_id')
    order_id = data.get('order_id')

    # Fetch user details
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Fetch order details
    order = Order.query.get(order_id)
    if not order or order.user_id != user_id:
        return jsonify({'message': 'Order not found or does not belong to the user'}), 404

    # Fetch order items
    order_items = OrderItem.query.filter_by(order_id=order_id).all()

    # Developer email from environment variables
    developer_email = os.environ.get('DEVELOPER_EMAIL')
    if not developer_email:
        return jsonify({'message': 'Developer email not configured'}), 500

    # Render the email templates
    user_email_body = render_template(
        'customer_email.html',
        customer_name=user.email,
        order=order,
        order_items=order_items,
        total_amount=order.total_amount
    )
    developer_email_body = render_template(
        'developer_email.html',
        customer_name=user.email,
        order=order,
        order_items=order_items,
        total_amount=order.total_amount
    )

    # Send email to customer
    customer_msg = Message(
        'Order Confirmation',
        recipients=[user.email],
        html=user_email_body
    )
    mail.send(customer_msg)

    # Send email to developer
    developer_msg = Message(
        'New Order Received',
        recipients=[developer_email],
        html=developer_email_body
    )
    mail.send(developer_msg)

    return jsonify({'message': 'Emails sent successfully'}), 200

def get_current_user():
    user_id = get_jwt_identity()
    return User.query.get(user_id)




from email.message import EmailMessage


def send_message(service, user_id, message):
    try:
        message = service.users().messages().send(userId='me', body=message).execute()
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












