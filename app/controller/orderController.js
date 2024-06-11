// orderController.js
const nodemailer = require('nodemailer');
const Order = require('../models/Order');

// Configure your email transporter
const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL_ADDRESS,
    pass: process.env.EMAIL_PASSWORD,
  },
});

exports.finalizeOrder = async (req, res) => {
  const { orderId } = req.body;

  try {
    const order = await Order.findById(orderId);

    if (!order) {
      return res.status(404).json({ error: 'Order not found' });
    }

    // Send email to customer
    const customerEmail = {
      from: process.env.EMAIL_ADDRESS,
      to: order.customer.email,
      subject: 'Order Confirmation',
      text: `Thank you for your order! Your order ID is ${orderId}.`,
    };

    await transporter.sendMail(customerEmail);

    // Send email to developer
    const developerEmail = {
      from: process.env.EMAIL_ADDRESS,
      to: process.env.DEVELOPER_EMAIL_ADDRESS,
      subject: 'New Order Received',
      text: `A new order (ID: ${orderId}) has been placed.`,
    };

    await transporter.sendMail(developerEmail);

    // Update order status
    order.status = 'PAID';
    await order.save();

    res.json({ success: true });
  } catch (error) {
    console.error('Error finalizing order:', error);
    res.status(500).json({ error: 'An error occurred while finalizing the order.' });
  }
};
