from datetime import datetime
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy 
from datetime import timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import get_jwt_identity
import jwt


db = SQLAlchemy()

def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return user

class TokenBlocklist(db.Model):
    __tablename__ = 'tokenblocklist'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    type = db.Column(db.String(16), nullable=False)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.user_id'),
        nullable=True,  # Make the field nullable
    )
    created_at = db.Column(
        db.DateTime,
        server_default=func.now(),
        nullable=False,
    )

class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(300), nullable=False)
    avatar_image = db.Column(db.String(300))
    
    orders = db.relationship('Order', backref='user', lazy=True)
    carts = db.relationship('Cart', backref='user', lazy=True)
   
    def __init__(self, username, email, password, avatar_image=None):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)
        self.avatar_image = avatar_image

    def compare_password(self, password):
        return check_password_hash(self.password, password)
    
    def generate_jwt(self):
        payload = {
            'user_id': self.user_id,
            'exp': datetime.now(timezone.utc) + timedelta(days=3)  # Token expires in 3 days
        }
        token = jwt.encode(payload, 'JWT_SECRET_KEY', algorithm='HS256')
        return token

    def create(self):
        db.session.add(self)
        db.session.commit()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key == "password":
                value = generate_password_hash(value)
            setattr(self, key, value)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "avatar_image": self.avatar_image
        }


class Product(db.Model):
    __tablename__ = 'product'
    product_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity_available = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200))

    def __init__(self, name, description, price, quantity_available, image_url):
        self.name = name
        self.description = description
        self.price = price
        self.quantity_available = quantity_available
        self.image_url = image_url

    def create(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        return {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "quantity_available": self.quantity_available,
            "image_url": self.image_url
        }

class NailSizeOption(db.Model):
    __tablename__ = 'nail_size_option'
    nail_size_option_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

    def __init__(self, name, description=None):
        self.name = name
        self.description = description

    def to_dict(self):
        return {
            'id': self.nail_size_option_id,
            'name': self.name,
            'description': self.description
        }

    def __repr__(self):
        return f'<NailSizeOption {self.name}>'

class Order(db.Model):
    __tablename__ = 'order'
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    street_address = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))  # Added state column
    country = db.Column(db.String(100))
    postal_code = db.Column(db.String(20))
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    order_items = db.relationship('OrderItem', backref='order', lazy=True)

    def __init__(self, user_id, total_amount, status, first_name=None, last_name=None, street_address=None, city=None, state=None, country=None, postal_code=None, created_at=None):
        self.user_id = user_id
        self.total_amount = total_amount
        self.first_name = first_name
        self.last_name = last_name
        self.street_address = street_address
        self.city = city
        self.state = state  # Assign state value
        self.country = country
        self.postal_code = postal_code
        self.status = status
        if created_at is not None:
            self.created_at = created_at

    def create(self):
        db.session.add(self)
        db.session.commit()

    def update(self, status):
        self.status = status
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "username": self.user.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.user.email,
            "street_address": self.street_address,
            "city": self.city,
            "country": self.country,
            "state": self.state,
            "postal_code": self.postal_code,
            "total_amount": self.total_amount,
            "status": self.status,
            "created_at": self.created_at
        }
    

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.order_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    nail_size_option_id = db.Column(db.Integer, db.ForeignKey('nail_size_option.nail_size_option_id'), nullable=False)
    left_hand_custom_size = db.Column(db.String(100))
    right_hand_custom_size = db.Column(db.String(100))

    product = db.relationship('Product', backref='order_items', lazy=True)
    nail_size_option = db.relationship('NailSizeOption', backref='order_items', lazy=True)

    def __init__(self, order_id, product_id, quantity, unit_price, nail_size_option_id, left_hand_custom_size=None, right_hand_custom_size=None):
        self.order_id = order_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.nail_size_option_id = nail_size_option_id
        self.left_hand_custom_size = left_hand_custom_size
        self.right_hand_custom_size = right_hand_custom_size

    def create(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        product = Product.query.get(self.product_id)
        nail_size_option = NailSizeOption.query.get(self.nail_size_option_id)
        return {
            "order_item_id": self.order_item_id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": product.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "nail_size_option": nail_size_option.name,  # Use the name attribute here
            "left_hand_custom_size": self.left_hand_custom_size,
            "right_hand_custom_size": self.right_hand_custom_size
        }


class Cart(db.Model):
    __tablename__ = 'cart'
    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)

    items = db.relationship('CartItem', backref='cart', cascade='all, delete-orphan')

    def __init__(self, user_id, total_amount):
        self.user_id = user_id
        self.total_amount = total_amount

    def create(self):
        db.session.add(self)
        db.session.commit()

    def update(self, status):
        self.status = status
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        return {
            "cart_id": self.cart_id,
            "user_id": self.user_id,
            "total_amount": self.total_amount
        }
    

class CartItem(db.Model):
    __tablename__ = 'cart_item'
    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.cart_id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    nail_size_option_id = db.Column(db.Integer, db.ForeignKey('nail_size_option.nail_size_option_id'), nullable=False)
    left_hand_custom_size = db.Column(db.String(100))
    right_hand_custom_size = db.Column(db.String(100))
  


    product = db.relationship('Product', backref='cart_items', lazy=True)
    nail_size_option = db.relationship('NailSizeOption', backref='cart_items', lazy=True)


    def __init__(self, cart_id, product_id, quantity, unit_price, nail_size_option_id, left_hand_custom_size=None, right_hand_custom_size=None):
        self.cart_id = cart_id
        self.product_id = product_id
        self.quantity = quantity
        self.unit_price = unit_price
        self.nail_size_option_id = nail_size_option_id
        self.left_hand_custom_size = left_hand_custom_size
        self.right_hand_custom_size = right_hand_custom_size


    def create(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def to_response(self):
        product = Product.query.get(self.product_id)
        nail_size_option = NailSizeOption.query.get(self.nail_size_option_id)
        return {
            "cart_item_id": self.cart_item_id,
            "cart_id": self.cart_id,
            "product_id": self.product_id,
            "product_name": product.name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "nail_size_option": nail_size_option.name,
            "left_hand_custom_size": self.left_hand_custom_size,
            "right_hand_custom_size": self.right_hand_custom_size
        }
