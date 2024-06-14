import os
from flask import Flask, request, jsonify,send_from_directory,redirect
from config import Config
from flask_mail import Mail
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.models import db, User , Order
from datetime import timedelta
import stripe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv 
from app.routes.order_routes import order_routes
import logging

app = Flask(__name__,static_url_path='/nails', static_folder='nails')
load_dotenv()
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
stripe.api_key = STRIPE_SECRET_KEY

YOUR_DOMAIN = 'http://localhost:3000'
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])




@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        order = Order.query.filter_by(order_id=order_id).first()

        # Ensure order and order_items exist
        if not order or not order.order_items:
            return jsonify({'error': 'Order not found or no items in the order'}), 400

        line_items = []
        for item in order.order_items:
            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item.product.name,
                    },
                    'unit_amount': int(item.product.price * 100),  # Amount in cents
                },
                'quantity': item.quantity,
            })

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=YOUR_DOMAIN + '/ordersuccesspage',
            cancel_url=YOUR_DOMAIN + '/cancel',
        )

        return jsonify({'url': session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/nails/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.static_folder, os.path.join('static\nails', filename))

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET')

def send_email(to_email, subject, body):
    sender_email = os.getenv('EMAIL_ADDRESS')
    sender_password = os.getenv('EMAIL_PASSWORD')
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = os.getenv('SMTP_PORT')
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        # Invalid payload
        print('Invalid payload')
        return jsonify(success=False), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('Invalid signature')
        return jsonify(success=False), 400

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        # Finalize the order and send emails
        order_details = finalize_order(payment_intent)
        send_confirmation_emails(order_details)

    return jsonify(success=True)

def finalize_order(payment_intent):
    # Your logic to finalize the order
    order_details = {
        'order_id': '12345',
        'amount': payment_intent['amount'],
        'customer_email': payment_intent['receipt_email'],
    }
    return order_details

def send_confirmation_emails(order_details):
    customer_email = order_details['customer_email']
    order_id = order_details['order_id']
    
    customer_subject = 'Order Confirmation'
    customer_body = f'Thank you for your purchase! Your order ID is {order_id}.'
    send_email(customer_email, customer_subject, customer_body)
    
    admin_subject = 'New Order Received'
    admin_body = f'A new order has been placed. Order ID: {order_id}.'
    send_email(os.getenv('ADMIN_EMAIL'), admin_subject, admin_body)

app.config.from_object(Config)

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize Flask-JWT-Extended
jwt = JWTManager(app)

# Initialize SQLAlchemy
db.init_app(app)

# Initialize Stripe
stripe.api_key = STRIPE_SECRET_KEY

# Define CORS headers
app.config['CORS_HEADERS'] = 'Content-Type'

# Configure Mail server
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=3)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = os.environ.get('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS')
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')

# Routes
from app.user.routes import user_blueprint
from app.product.routes import product_blueprint
from app.cart.routes import cart_blueprint
from app.order.routes import order_blueprint
from app.nail_sizes.routes import nail_sizes_blueprint

app.register_blueprint(nail_sizes_blueprint)
app.register_blueprint(order_routes, url_prefix='/api/orders')
app.register_blueprint(user_blueprint)
app.register_blueprint(product_blueprint)
app.register_blueprint(cart_blueprint)
app.register_blueprint(order_blueprint)


# JWT Configurations
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.user_id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    return User.query.filter_by(user_id=identity).one_or_none()

if __name__ == '__main__':
    app.run(port=5000)  # Run the application on port 5000
