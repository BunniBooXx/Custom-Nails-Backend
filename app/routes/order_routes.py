from flask import Blueprint, request, jsonify
import os
import smtplib

from app.models import Order

order_routes = Blueprint('order_routes', __name__)

@order_routes.route('/finalize-order', methods=['POST'])
def finalize_order():
    order_id = request.json.get('orderId')

    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Send email to customer
        customer_email = {
            'from': os.environ.get('EMAIL_ADDRESS'),
            'to': order.customer.email,
            'subject': 'Order Confirmation',
            'body': f'Thank you for your order! Your order ID is {order_id}.'
        }
        send_email(customer_email)

        # Send email to developer
        developer_email = {
            'from': os.environ.get('EMAIL_ADDRESS'),
            'to': os.environ.get('DEVELOPER_EMAIL_ADDRESS'),
            'subject': 'New Order Received',
            'body': f'A new order (ID: {order_id}) has been placed.'
        }
        send_email(developer_email)

        # Update order status
        order.status = 'PAID'
        order.save()

        return jsonify({'success': True})
    except Exception as e:
        print(f'Error finalizing order: {e}')
        return jsonify({'error': 'An error occurred while finalizing the order.'}), 500

def send_email(email_data):
    smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
    smtp_server.starttls()
    smtp_server.login(os.environ.get('EMAIL_ADDRESS'), os.environ.get('EMAIL_PASSWORD'))
    msg = f"From: {email_data['from']}\nTo: {email_data['to']}\nSubject: {email_data['subject']}\n\n{email_data['body']}"
    smtp_server.sendmail(email_data['from'], email_data['to'], msg)
    smtp_server.quit()
