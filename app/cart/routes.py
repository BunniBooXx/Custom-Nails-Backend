from flask import Flask, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Product, Cart, CartItem
from flask import Blueprint

cart_blueprint = Blueprint("cart", __name__, url_prefix="/cart")


@cart_blueprint.route('/add_to_cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    data = request.json
    user_id = get_jwt_identity()  # Assuming you have user authentication
    product_id = data.get('product_id')
    quantity = data.get('quantity')

    if not product_id or not quantity:
        return jsonify({'error': 'Product ID and quantity are required'}), 400

    user_cart = Cart.query.filter_by(user_id=user_id).first()
    if not user_cart:
        # Initialize the cart with a total_amount of 0
        user_cart = Cart(user_id=user_id, total_amount=0)
        db.session.add(user_cart)

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    if product.quantity_available < quantity:
        return jsonify({'error': 'Not enough quantity available'}), 400

    cart_item = CartItem.query.filter_by(cart_id=user_cart.cart_id, product_id=product_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(
            cart_id=user_cart.cart_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price
        )

    product.quantity_available -= quantity

    # Calculate the updated total_amount of the cart
    user_cart.total_amount += (product.price * quantity)

    db.session.add(cart_item)
    db.session.commit()

    return jsonify({'message': 'Product added to cart successfully'})


@cart_blueprint.route('/update/<int:cart_id>', methods=['PUT'])
@jwt_required()
def update_cart(cart_id):
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id, cart_id=cart_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    data = request.json

    # Update cart details
    if 'total_amount' in data:
        # Calculate total amount from cart items
        total_amount = 0
        cart_items = CartItem.query.filter_by(cart_id=cart_id).all()
        for cart_item in cart_items:
            product = Product.query.get(cart_item.product_id)
            total_amount += product.price * cart_item.quantity

        # Update total_amount of the cart
        cart.total_amount = total_amount

    db.session.commit()
    return jsonify({'message': 'Cart updated successfully', 'cart': cart.to_response()})


@cart_blueprint.route('/delete_all_items/<int:cart_id>', methods=['DELETE'])
@jwt_required()
def delete_all_items_in_cart(cart_id):
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id, cart_id=cart_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    try:
        cart_items = CartItem.query.filter_by(cart_id=cart_id).all()
        for cart_item in cart_items:
            db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'All items in cart deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cart_blueprint.route('/delete_item/<int:cart_id>/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item_from_cart(cart_id, item_id):
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id, cart_id=cart_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    cart_item = CartItem.query.get(item_id)
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404

    try:
        # Get the product associated with the cart item
        product = Product.query.get(cart_item.product_id)

        # Calculate the cost of the deleted item
        deleted_item_cost = product.price * cart_item.quantity

        # Update the total amount of the cart
        cart.total_amount -= deleted_item_cost

        # Delete the cart item
        db.session.delete(cart_item)
        db.session.commit()

        return jsonify({'message': 'Cart item deleted successfully', 'new_total_amount': cart.total_amount}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@cart_blueprint.route('/read/<int:cart_id>', methods=['GET'])
@jwt_required()
def get_cart(cart_id):
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id, cart_id=cart_id).first()

    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    cart_data = {'items': []}
    total_price = 0

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        item_data = {
            'product_id': product.product_id,
            'name': product.name,
            'image': product.image_url,
            'price': product.price,
            'quantity': cart_item.quantity
        }
        total_price += product.price * cart_item.quantity
        cart_data['items'].append(item_data)

    cart_data['total_price'] = total_price

    return jsonify(cart_data)

