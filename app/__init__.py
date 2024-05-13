import os
from flask import Flask, request, jsonify,send_from_directory
from config import Config
from flask_mail import Mail
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.models import db, User 
from datetime import timedelta
import stripe

app = Flask(__name__,static_url_path='/nails', static_folder='nails')
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

@app.route('/nails/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.static_folder, os.path.join('static\nails', filename))

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

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
stripe.api_key = 'pk_test_51OwSCeEBwfjW7s9fwT5GlYGVHY7f3YPeRxHEqbV8YJQN139JgZpuJjTgZIzoEmeds2FUi91q8TbSJVq1gxQbczmf00ht6oOGGU'

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

app.register_blueprint(user_blueprint)
app.register_blueprint(product_blueprint)
app.register_blueprint(cart_blueprint)
app.register_blueprint(order_blueprint)

# Stripe Checkout Session Route
@app.route('/create-checkout-session/<int:order_id>', methods=['POST'])
def create_checkout_session(order_id):
    try:
        data = request.json
        quantity = data.get('quantity', 1)  # Default quantity is 1
        # Retrieve order details here based on the order_id
        # For example:
        # order = Order.query.get(order_id)
        
        # Replace this with your product price ID
        price_id = 'PRICE_ID_HERE'
        
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': price_id,
                    'quantity': quantity,
                },
            ],
            mode='payment',
            success_url='http://localhost:3000/order/success/' + str(order_id),  # Your success URL
            cancel_url='http://localhost:3000/order/canceled/' + str(order_id),  # Your cancel URL
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({'url': checkout_session.url}), 200

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
