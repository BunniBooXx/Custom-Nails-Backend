import os
from flask import Flask, request, jsonify, send_from_directory 

from config import Config
from flask_mail import Mail, Message
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.models import db, User, Order
from datetime import timedelta
import stripe
from dotenv import load_dotenv

app = Flask(__name__, static_url_path='/nails', static_folder='nails')
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

@app.route('/send-emails', methods=['POST'])
def send_emails():
    order_id = request.json.get('orderId')

    try:
        # Fetch order details from your database
        order = fetch_order_from_database(order_id)

        # Send email to customer
        customer_email = Message(
            'Order Confirmation',
            sender=app.config['MAIL_USERNAME'],
            recipients=[order.customer_email]
        )
        customer_email.body = f"Thank you for your order! Your order ID is {order_id}."
        mail.send(customer_email)

        # Send email to developer
        developer_email = Message(
            'New Order Received',
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['DEVELOPER_EMAIL']]
        )
        developer_email.body = f"A new order (ID: {order_id}) has been placed."
        mail.send(developer_email)

        # Update order status in the database
        update_order_status_in_database(order_id, 'PAID')

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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

# Configure JWT Access Token Expiration
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=3)

# Configure Mail server
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
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
