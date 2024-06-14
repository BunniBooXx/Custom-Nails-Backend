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
            success_url=YOUR_DOMAIN + f'/ordersuccesspage/{order_id}',
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

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET')

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
        order_id = payment_intent['metadata'].get('order_id')
        
        if not order_id:
            print('Order ID not found in metadata')
            return jsonify(success=False), 400
        
        order = Order.query.get(order_id)
        if not order:
            print(f'Order with ID {order_id} not found')
            return jsonify(success=False), 404
        
        # Finalize the order (you can implement this logic as per your requirements)
        order.finalize_order(payment_intent)

        # Send confirmation emails
        send_confirmation_emails(order)

    return jsonify(success=True)

def send_confirmation_emails(order):
    # Send confirmation email to customer
    customer_email = order.customer_email
    customer_subject = 'Order Confirmation'
    customer_body = f'Thank you for your purchase! Your order ID is {order.order_id}.'
    send_email(customer_email, customer_subject, customer_body)

    # Send notification email to admin
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_subject = 'New Order Received'
    admin_body = f'A new order has been placed. Order ID: {order.order_id}.'
    send_email(admin_email, admin_subject, admin_body)

def send_email(to_email, subject, body):
    sender_email = app.config['MAIL_USERNAME']
    sender_password = app.config['MAIL_PASSWORD']
    smtp_server = app.config['MAIL_SERVER']
    smtp_port = app.config['MAIL_PORT']

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
            print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")

        
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
# Configure Mail server
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'your_email@example.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'your_password')

# Ensure these environment variables are properly set in your .env file or environment


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
