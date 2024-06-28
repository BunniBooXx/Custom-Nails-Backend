from flask import Blueprint, request, jsonify
from app.models import db, Product
import os
import stripe
from werkzeug.utils import secure_filename

product_blueprint = Blueprint("product_blueprint", __name__, url_prefix="/product")

# Define the upload folder
UPLOAD_FOLDER = 'nails'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}



# Function to save uploaded image
def save_image(image):
    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    # Define the image filename
    image_filename = secure_filename(image.filename)
    image_path = os.path.join(UPLOAD_FOLDER, image_filename)
    
    # Save the image file
    image.save(image_path)
    
    # Return the image URL
    return f'https://custom-nails-backend.onrender.com/nails/{image_filename}'  # Return the full URL of the image

@product_blueprint.route('/create', methods=['POST'])
def create_product():
    # Get form data
    name = request.form.get('name')
    description = request.form.get('description')
    price = request.form.get('price')
    quantity_available = request.form.get('quantity_available')
    image = request.files.get('image')

    # Check if any form data is missing
    if not all([name, description, price, quantity_available, image]):
        return jsonify({'error': 'Missing required field(s)'}), 400

    # Save the image and get the image URL
    image_url = save_image(image)

    # Create a new product instance with the provided data
    product = Product(name=name, description=description, price=price, quantity_available=quantity_available, image_url=image_url)

    # Add the product to the database session and commit changes
    db.session.add(product)
    db.session.commit()

    # Return a JSON response indicating success and the created product data
    return jsonify({'success': True, 'message': 'Product created successfully', 'data': product.to_response()}), 201

@product_blueprint.route('/update/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    data = request.json
    try:
        for key, value in data.items():
            setattr(product, key, value)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product updated successfully', 'data': product.to_response()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_blueprint.route('/delete/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    try:
        db.session.delete(product)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_blueprint.route('/read_all', methods=['GET'])
def get_products():
    try:
        products = Product.query.all()
        response = [{'id': product.product_id, 'name': product.name, 'price': product.price, 'description': product.description, 'image_url': product.image_url} for product in products]
        return jsonify({'success': True, 'message': 'Products retrieved successfully', 'data': response})
    except Exception as e:
        print(e)  # Print the error message
        return jsonify({'error': str(e)}), 500

@product_blueprint.route('/read/<int:product_id>', methods=['GET'])
def get_product(product_id):
    try:
        product = Product.query.get(product_id)
        if product:
            image_url = product.image_url 
            return jsonify({
                'success': True,
                'message': 'Product retrieved successfully',
                'data': {
                    'id': product.product_id,
                    'name': product.name,
                    'price': product.price,
                    'description': product.description,
                    'image_url': image_url  # Only the relative image URL
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_blueprint.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    try:
        data = request.json
        line_items = [
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': item['name'],
                        'images': [item['image']],
                    },
                    'unit_amount': int(item['price'] * 100),  # Stripe expects the amount in cents
                },
                'quantity': item['quantity'],
            } for item in data['items']
        ]

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url='http://custom-nails-backend.onrender.com/ordersuccesspage',  # Replace with your frontend success URL
            cancel_url='http://custom-nails-backend.onrender.com/cancel',  # Replace with your frontend cancel URL
        )

        return jsonify({'clientSecret': session.client_secret})
    except Exception as e:
        return jsonify({'error': str(e)}), 500