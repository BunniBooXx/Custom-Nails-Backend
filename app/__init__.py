import os
from flask import Flask, request, jsonify, send_from_directory


from config import Config
import sys
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required
from flask_cors import CORS
from app.models import db, User, Order
from datetime import timedelta
import stripe
from dotenv import load_dotenv
from flask import Flask, render_template, send_from_directory

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder=os.path.join(PROJECT_ROOT, 'templates'),
            static_url_path='/nails', 
            static_folder=os.path.join(PROJECT_ROOT, 'nails'))

load_dotenv()

import os
from flask import Flask, render_template

import logging
from logging import FileHandler, WARNING

file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(WARNING)
app.logger.addHandler(file_handler)


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

# Define the fetch_order_from_database and update_order_status_in_database functions
def fetch_order_from_database(order_id):
    order = Order.query.get(order_id)
    print(f"Fetched order from database: {order}")
    return order

def update_order_status_in_database(order_id, status):
    order = Order.query.get(order_id)
    if order:
        print(f"Updating order status for order {order_id} to {status}")
        order.status = status
        db.session.commit()
        print(f"Order status updated successfully")
        return order
    print(f"Order with ID {order_id} not found")
    return None

from flask_jwt_extended import get_jwt_identity
import logging

logging.basicConfig(level=logging.DEBUG)

from flask import render_template
import smtplib
from email.mime.text import MIMEText
from flask import jsonify, render_template
from flask_jwt_extended import get_jwt_identity, jwt_required

from flask_mail import Message, Mail
mail = Mail(app)

def send_email(recipient, subject, body):
    msg = Message(subject, recipients=[recipient])
    msg.html = body
    mail.send(msg)


@app.route('/send-emails/<int:order_id>', methods=['POST'])
@jwt_required()
def send_emails(order_id):
    try:
        # Get the current user from the JWT token
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Fetch the order details
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Prepare the email content
        order_items = order.order_items
        total_amount = order.total_amount

        # Render the email template
        customer_email_body = render_template('customer_email.html', order=order, order_items=order_items, total_amount=total_amount)
        developer_email_body = render_template('developer_email.html', order=order, order_items=order_items, total_amount=total_amount)

        # Send email to customer
        send_email(user.email, 'Order Confirmation', customer_email_body)

        # Send email to developer
        send_email(app.config['DEVELOPER_EMAIL'], 'New Order Received', developer_email_body)

        # Update order status in the database
        update_order_status_in_database(order_id, 'PAID')

        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error sending emails for order {order_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

app.config.from_object(Config)

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

# Configure JWT Access Token Expiration
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=3)

# Configure Mail server
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS')
app.config['MAILJET_API_KEY'] = os.getenv('MAILJET_API_KEY')
app.config['MAILJET_SECRET_KEY'] = os.getenv('MAILJET_SECRET_KEY')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAILJET_SECRET_KEY')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAILJET_FROM_EMAIL')
app.config['DEVELOPER_EMAIL'] = os.getenv('DEVELOPER_EMAIL')



# Ensure these environment variables are properly set in your .env file or environment

# Routes
from app.user.routes import user_blueprint
from app.product.routes import product_blueprint
from app.cart.routes import cart_blueprint
from app.order.routes import order_blueprint
from app.routes.order_routes import order_routes
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
