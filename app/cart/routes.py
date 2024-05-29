from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Product, Cart, CartItem, NailSizeOption
from flask import Blueprint

cart_blueprint = Blueprint("cart", __name__, url_prefix="/cart")


@cart_blueprint.route('/add_to_cart', methods=['POST'])
@jwt_required()
def add_to_cart():
    data = request.json
    user_id = get_jwt_identity()
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    nail_size_option_id = data.get('nail_size_option_id')
    left_hand_custom_size = data.get('left_hand_custom_size')
    right_hand_custom_size = data.get('right_hand_custom_size')

    if not product_id or not quantity or not nail_size_option_id:
        return jsonify({'error': 'Product ID, quantity, and nail size option are required'}), 400

    user_cart = Cart.query.filter_by(user_id=user_id).first()
    if not user_cart:
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
            unit_price=product.price,
            nail_size_option_id=nail_size_option_id,
            left_hand_custom_size=left_hand_custom_size,
            right_hand_custom_size=right_hand_custom_size
        )
        db.session.add(cart_item)

    product.quantity_available -= quantity
    user_cart.total_amount += (product.price * quantity)
    db.session.commit()

    return jsonify({'message': 'Product added to cart successfully'})

@cart_blueprint.route('/update', methods=['PUT'])
@jwt_required()
def update_cart():
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    data = request.json

    # Update cart details
    if 'total_amount' in data:
        # Calculate total amount from cart items
        total_amount = 0
        cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
        for cart_item in cart_items:
            product = Product.query.get(cart_item.product_id)
            total_amount += product.price * cart_item.quantity

        # Update total_amount of the cart
        cart.total_amount = total_amount

    db.session.commit()
    return jsonify({'message': 'Cart updated successfully', 'cart': cart.to_response()})


@cart_blueprint.route('/delete_all_items', methods=['DELETE'])
@jwt_required()
def delete_all_items_in_cart():
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    try:
        cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
        for cart_item in cart_items:
            db.session.delete(cart_item)
        db.session.commit()
        return jsonify({'message': 'All items in cart deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@cart_blueprint.route('/delete_item/<int:item_id>', methods=['DELETE', 'OPTIONS'])
@jwt_required()
def delete_item_from_cart(item_id):
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'DELETE'
        return response

    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    
    cart_item = CartItem.query.filter_by(cart_id=cart.cart_id, product_id=item_id).first()
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

        # Fetch updated cart items
        cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
        total_price = sum(product.price * item.quantity for item in cart_items)

        return jsonify({'message': 'Cart item deleted successfully', 'new_total_amount': total_price}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@cart_blueprint.route('/add_quantity/<int:item_id>', methods=['PUT'])
@jwt_required()
def add_quantity_to_cart(item_id):
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'error': 'Cart not found'}), 404
    cart_item = CartItem.query.get(item_id)
    if not cart_item:
        return jsonify({'error': 'Cart item not found'}), 404

    data = request.json
    quantity = data.get('quantity')

    if not quantity:
        return jsonify({'error': 'Quantity is required'}), 400

    try:
        # Get the product associated with the cart item
        product = Product.query.get(cart_item.product_id)

        # Calculate the cost of the added quantity
        added_quantity_cost = product.price * quantity

        # Update the total amount of the cart
        cart.total_amount += added_quantity_cost

        # Update the quantity of the cart item
        cart_item.quantity += quantity

        db.session.commit()

        return jsonify({'message': 'Quantity added to cart successfully', 'new_total_amount': cart.total_amount}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@cart_blueprint.route('/read', methods=['GET'])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()
    cart = Cart.query.filter_by(user_id=user_id).first()

    if not cart:
        return jsonify({'error': 'Cart not found'}), 404

    cart_items = CartItem.query.filter_by(cart_id=cart.cart_id).all()
    cart_data = {'cart_id': cart.cart_id, 'items': []}
    total_price = 0

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        nail_size_option = NailSizeOption.query.get(cart_item.nail_size_option_id)
        item_data = {
            'product_id': product.product_id,
            'name': product.name,
            'image': product.image_url,
            'price': product.price,
            'quantity': cart_item.quantity,
            'nail_size_option': nail_size_option.name,
            'left_hand_custom_size': cart_item.left_hand_custom_size,
            'right_hand_custom_size': cart_item.right_hand_custom_size
        }
        total_price += product.price * cart_item.quantity
        cart_data['items'].append(item_data)

    cart_data['total_price'] = total_price

    return jsonify(cart_data)


