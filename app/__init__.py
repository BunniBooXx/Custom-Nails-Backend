import os
from flask import Flask, request, jsonify, redirect, url_for, session, render_template, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask_caching import Cache
from flask_migrate import Migrate
from logging.handlers import RotatingFileHandler
from flask_session import Session
from flask_talisman import Talisman
import stripe
import logging
from app.models import User, Product, Order, OrderItem, db
from app.order.routes import order_blueprint
from app.user.routes import user_blueprint
from app.product.routes import product_blueprint
from app.cart.routes import cart_blueprint

# Define the path to the client secrets file
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), 'config', 'client_secrets.json')

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

app = Flask(__name__, template_folder='templates', static_url_path='/nails', static_folder='nails')

# Additional configuration for hosted environment
app.config['ENV'] = 'production'
app.config['DEBUG'] = False
app.config.from_object(os.getenv('APP_SETTINGS'))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Content Security Policy Configuration
csp = {
    'default-src': ["'self'"],
    'script-src': [
        "'self'", "'unsafe-inline'", "'unsafe-eval'",
        'https://js.stripe.com',
        'https://custom-nails-backend.example.com',  # Replace with your backend domain
        'https://nail-shop.example.com'  # Replace with your frontend domain
    ],
    'connect-src': [
        "'self'",
        'https://api.stripe.com',
        'https://custom-nails-backend.example.com',  # Replace with your backend domain
        'https://nail-shop.example.com'  # Replace with your frontend domain
    ],
    'frame-src': [
        'https://js.stripe.com',
        'https://custom-nails-backend.example.com',  # Replace with your backend domain
        'https://nail-shop.example.com'  # Replace with your frontend domain
    ],
    'img-src': [
        "'self'", 'data:', 'https://*.stripe.com',
        'https://custom-nails-backend.example.com',  # Replace with your backend domain
        'https://nail-shop.example.com'  # Replace with your frontend domain
    ],
    'style-src': [
        "'self'", "'unsafe-inline'",
        'https://custom-nails-backend.example.com',  # Replace with your backend domain
        'https://nail-shop.example.com'  # Replace with your frontend domain
    ]
}

# Initialize Talisman with the CSP configuration
Talisman(app, content_security_policy=csp)

# Set up CORS
CORS(app, resources={r"/*": {"origins": ["https://localhost:3000", "https://nail-shop.onrender.com"]}}, supports_credentials=True)

# Ensure a secret key is set for session management
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'supersecretkey')

# Initialize extensions
mail = Mail(app)
jwt = JWTManager(app)
cache = Cache(config={'CACHE_TYPE': 'simple'})
cache.init_app(app)
db.init_app(app)
migrate = Migrate(app, db)
Session(app)

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'flask-session:'
app.config['SESSION_FILE_DIR'] = '/tmp/flask-session/'

# Create session directory if it does not exist
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])
    print(f"Created session directory: {app.config['SESSION_FILE_DIR']}")
else:
    print(f"Session directory exists: {app.config['SESSION_FILE_DIR']}")

# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Register blueprints
app.register_blueprint(user_blueprint, url_prefix='/user')
app.register_blueprint(product_blueprint, url_prefix='/product')
app.register_blueprint(order_blueprint, url_prefix='/order')
app.register_blueprint(cart_blueprint, url_prefix='/cart')

# Example route to set a cookie
@app.route('/')
def index():
    response = make_response("Welcome to your Flask application!")
    response.set_cookie(
        'my_cookie', 
        'cookie_value', 
        secure=True, 
        httponly=True, 
        samesite='None'
    )
    return response

@app.route('/create-checkout-session', methods=['POST'])
@jwt_required()
def create_checkout_session():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        if not order_id:
            return jsonify({'error': 'Missing order_id in request body'}), 400

        # Check if the checkout session is already cached
        cache_key = f'checkout_session_{order_id}'
        cached_session = cache.get(cache_key)
        if cached_session:
            return jsonify({'url': cached_session.url})

        # Fetch order details from your database
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Create a new Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Order {order_id}',
                        },
                        'unit_amount': int(order.total_amount * 100),  # Convert to cents
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=f"https://nail-shop.onrender.com/ordersuccesspage/{order_id}",
            cancel_url=f"https://nail-shop.onrender.com/cancel",
            metadata={
                'order_id': order_id
            }
        )

        # Cache the checkout session
        cache.set(cache_key, session, timeout=3600)  # Cache for 1 hour

        return jsonify({
            'sessionId': session.id,
            'publishableKey': app.config['STRIPE_PUBLISHABLE_KEY']
        }), 200

    except Exception as e:
        app.logger.error(f'Error creating checkout session: {e}')
        return jsonify({'error': 'Failed to create checkout session', 'message': str(e)}), 500

@app.after_request
def set_csp_header(response):
    csp = (
        "default-src 'self'; "
        "connect-src *; "  # Allow all connections for debugging
        "frame-src 'self' https://js.stripe.com https://hooks.stripe.com https://connect-js.stripe.com https://checkout.stripe.com; "
        "script-src 'self' 'unsafe-inline' https://js.stripe.com https://maps.googleapis.com https://connect-js.stripe.com https://checkout.stripe.com; "
        "style-src 'self' 'unsafe-inline' sha256-0hAheEzaMe6uXIKV4EehS9pu1am1lj/KnnzrOYqckXk=; "
        "img-src 'self' data: https://*.stripe.com; "
        "report-uri /csp-report;"
    )
    print("Setting CSP header:", csp)
    response.headers['Content-Security-Policy'] = csp
    return response

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
    print(f"State set in session: {state}")
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

def get_gmail_service():
    try:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file('app/config/nail-shop.json')
        return build('gmail', 'v1', credentials=credentials)
    except ValueError as e:
        app.logger.error(f"ValueError: {str(e)}")
        return None
    except Exception as e:
        app.logger.error(f"Exception in get_gmail_service: {str(e)}")
        return None

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

if __name__ == '__main__':
    port = int(os.getenv('PORT', 1000))
    app.run(host='0.0.0.0', port=port)














