from flask import jsonify, request
from flask_mail import Message
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mail
from app.models import db, Order, OrderItem, User, Product, CartItem, Cart, NailSizeOption
from flask import Blueprint

order_blueprint = Blueprint("order", __name__, url_prefix="/order")

@order_blueprint.route('/create_preliminary_order', methods=['POST'])
@jwt_required()
def create_preliminary_order():
    data = request.json
    user_id = get_jwt_identity()  # Retrieve user ID from JWT
    total_amount = data.get('total_amount')

    # Create a preliminary order with user information
    order = Order(user_id=user_id, total_amount=total_amount, status='Processing')
    
    db.session.add(order)
    db.session.commit()

    # Fetch the user's cart
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'success': False, 'error': 'Cart not found'}), 404

    # Create order items from cart items
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.product.price,
            nail_size_option_id=item.nail_size_option_id
        )
        db.session.add(order_item)

    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Preliminary order created successfully', 'order_id': order.order_id}), 201

@order_blueprint.route('/update_order_with_user_info/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order_with_user_info(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404

    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    street_address = data.get("street_address")
    city = data.get("city")
    state = data.get("state")
    country = data.get("country")
    postal_code = data.get("postal_code")

    # Update order details with user information
    order.first_name = first_name
    order.last_name = last_name
    order.street_address = street_address
    order.city = city
    order.state = state
    order.country = country
    order.postal_code = postal_code
    order.status = 'Updating order'  # Set status to 'Updating order'

    db.session.commit()

    return jsonify({'success': True, 'message': 'Order updated with user information successfully'}), 200

@order_blueprint.route('/finalize-order', methods=['POST'])
def finalize_order():
    try:
        data = request.get_json()
        order_id = data.get('orderId')
        amount = data.get('amount')

        order = Order.query.get(order_id)
        if order:
            order.status = 'paid'
            order.total_amount = amount / 100  # Convert from cents to dollars
            db.session.commit()

            send_order_confirmation_email(order)

            return jsonify({'clientSecret': 'dummy_client_secret'})
        else:
            return jsonify({'error': 'Order not found'}), 404
    except Exception as e:
        print(f'Error finalizing order: {e}')
        return jsonify({'error': 'Internal server error'}), 500

def send_order_email(order, order_items):
    msg = Message("New Order Received",
                  sender="bunnybubblenails@gmail.com",
                  recipients=["bunnybubblenails@gmail.com"])
    msg.body = f"New order received!\nOrder ID: {order.order_id}\nTotal Amount: {order.total_amount}\n\nProducts:\n"
    for item in order_items:
        product = Product.query.get(item.product_id)
        msg.body += f"Product ID: {item.product_id}\nName: {product.name}\nQuantity: {item.quantity}\nUnit Price: {item.unit_price}\n\n"
    mail.send(msg)

def send_order_confirmation_email(order):
    user = User.query.get(order.user_id)
    if user:
        msg = Message("Order Confirmation",
                      sender="bunnybubblenails@gmail.com",
                      recipients=[user.email])  # Assuming you have an 'email' field in your User model
        msg.body = f"Your order has been received!\nOrder ID: {order.order_id}\nTotal Amount: {order.total_amount}\n\nThank you for shopping with us!"
        mail.send(msg)


@order_blueprint.route('/details/<int:order_id>', methods=['GET'])
@jwt_required()
def order_details(order_id):
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        order_items = OrderItem.query.filter_by(order_id=order_id).all()
        
        # Example response structure
        response = {
            'order_id': order.order_id,
            'total_amount': order.total_amount,
            'order_items': [{'product_name': item.product.name, 'quantity': item.quantity} for item in order_items]
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_blueprint.route('/payment_success', methods=['POST'])
@jwt_required()
def handle_payment_success():
    # Process the payment success webhook from Stripe
    order_id = request.json.get('order_id')
    if not order_id:
        return jsonify({'error': 'Order ID not provided in webhook payload'}), 400
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404
    
    # Update order status to indicate payment success
    order.status = 'Processing'  # Or any other appropriate status
    db.session.commit()

     
    # Send order confirmation email to shop owner
    order_items = OrderItem.query.filter_by(order_id=order_id).all()
    send_order_email(order, order_items)

    # Send order confirmation email to user
    send_order_confirmation_email(order)
    
    return jsonify({'message': 'Order status updated successfully'}), 200

@order_blueprint.route('/read/<int:order_id>', methods=['GET'])
@jwt_required()
def read_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    order_data = {
        'order_id': order.order_id,
        'user_id': order.user_id,
        'email': order.user.email,  # Retrieve the user's email from the User model
        'first_name': order.first_name,
        'last_name': order.last_name,
        'street_address': order.street_address,
        'city': order.city,
        'country': order.country,
        'state': order.state,
        'postal_code': order.postal_code,
        'total_amount': order.total_amount,
        'status': order.status,
        'created_at': order.created_at,
        'order_items': [
            {
                'order_item_id': order_item.order_item_id,
                'product_id': order_item.product_id,
                'quantity': order_item.quantity,
                'unit_price': order_item.unit_price,
                'nail_size_option_id': order_item.nail_size_option_id,
                'left_hand_custom_size': order_item.left_hand_custom_size,
                'right_hand_custom_size': order_item.right_hand_custom_size
            }
            for order_item in order.order_items
        ]
    }

    return jsonify(order_data), 200
