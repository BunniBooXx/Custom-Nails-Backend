from flask import jsonify, request
from flask_mail import Message
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import mail
from app.models import db, Order, OrderItem, User, Product, CartItem, Cart
from flask import Blueprint

order_blueprint = Blueprint("order", __name__, url_prefix= "/order" )

# Preliminary Order 
@order_blueprint.route('/create_preliminary_order', methods=['POST'])
@jwt_required()
def create_preliminary_order():
    data = request.json
    user_id = get_jwt_identity()  # Retrieve user ID from JWT
    total_amount = data.get('total_amount')
    first_name = data.get('first_name')  # Extract first name from request data if available
    last_name = data.get('last_name')    # Extract last name from request data if available
    address = data.get('address')        # Extract address from request data if available
    
    # Create a preliminary order with user information
    order = Order(user_id=user_id, total_amount=total_amount, status='Processing')
    
    # Set first name, last name, and address if available
    if first_name is not None:
        order.first_name = first_name
    if last_name is not None:
        order.last_name = last_name
    if address is not None:
        order.address = address
    
    db.session.add(order)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Preliminary order created successfully', 'order_id': order.order_id}), 201


# Order with User Info API route
@order_blueprint.route('/update_order_with_user_info/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order_with_user_info(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    data = request.json
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    address = data.get("address")
    
    # Update order details with user information
    order.first_name = first_name
    order.last_name = last_name
    order.address = address
    order.status = 'Updating order'  # Set status to 'Updating order'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Order updated with user information successfully'}), 200

@order_blueprint.route('/finalize_order/<int:order_id>', methods=['PUT'])
@jwt_required()
def finalize_order(order_id):
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'error': 'Order not found'}), 404
    
    # Fetch the user's cart
    user_id = order.user_id
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        return jsonify({'success': False, 'error': 'Cart not found'}), 404

    # Delete the cart items and the cart
    CartItem.query.filter_by(cart_id=cart.cart_id).delete()
    db.session.delete(cart)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Order finalized successfully'}), 200


def send_order_email(order, order_items):
    msg = Message("New Order Received",
                  sender="bunnybubblenails@gmail.com",
                  recipients=["bunnybubblenails@gmail.com"])
    msg.body = f"New order received!\nOrder ID: {order.order_id}\nTotal Amount: {order.total_amount}\n\nProducts:\n"
    for item in order_items:
        product = Product.query.get(item['product_id'])
        msg.body += f"Product ID: {item['product_id']}\nName: {product.name}\nQuantity: {item['quantity']}\nUnit Price: {item['unit_price']}\n\n"
    mail.send(msg)

def send_order_confirmation_email(order):
    user = User.query.get(order.user_id)
    if user:
        msg = Message("Order Confirmation",
                      sender="bunnybubblenails@gmail.com",
                      recipients=[user.email])  # Assuming you have an 'email' field in your User model
        msg.body = f"Your order has been received!\nOrder ID: {order.order_id}\nTotal Amount: {order.total_amount}\n\nThank you for shopping with us!"
        mail.send(msg)

# Handle Payment Success API route
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
    send_order_email(order)

    # Send order confirmation email to user
    send_order_confirmation_email(order)
    
    return jsonify({'message': 'Order status updated successfully'}), 200

