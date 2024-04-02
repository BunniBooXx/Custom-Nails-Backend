from flask import Flask,  request,  session
from flask import request,  jsonify
from datetime import timedelta
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models import db, Product
from flask import Blueprint

product_blueprint = Blueprint("product_blueprint", __name__, url_prefix= "/product" )

@product_blueprint.route('/create', methods=['POST'])
def create_product():
    """
    Create a new product.

    Expected JSON data:
    {
        "name": "Product Name",
        "description": "Product Description",
        "price": 10.99,
        "quantity_available": 100,
        "image_url": "https://example.com/image.jpg"
    }
    """
    data = request.json

    # Ensure that all required fields are present in the request
    required_fields = ["name", "description", "price", "quantity_available", "image_url"]
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    # Create a new product instance with the provided data
    product = Product(**data)

    # Add the product to the database session and commit changes
    db.session.add(product)
    db.session.commit()

    # Return a JSON response indicating success and the created product data
    return jsonify({'message': 'Product created successfully', 'product': product.to_response()}), 201



@product_blueprint.route('/update/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    data = request.json
    for key, value in data.items():
        setattr(product, key, value)
    db.session.commit()
    return jsonify({'message': 'Product updated successfully', 'product': product.to_response()})

@product_blueprint.route('/delete/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product deleted successfully'})

@product_blueprint.route('/read_all', methods=['GET'])
def get_products():
    products = Product.query.all()
    response = []
    for product in products:
        response.append({
            'name': product.name,
            'price': product.price,
            'description':product.description,
            'image_url': product.image_url
        })
    return jsonify({'success': True, 'message': 'Products retrieved successfully', 'data': response})

@product_blueprint.route('/read/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if product:
        return jsonify({'success': True, 'message': 'Product retrieved successfully', 'data': {
            'name': product.name,
            'price': product.price,
            'description': product.description,
            'image_url': product.image_url
        }})
    else:
        return jsonify({'success': False, 'error': 'Product not found'}), 404
