from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import db, Product, Cart, CartItem, NailSizeOption
from flask import Blueprint

nail_sizes_blueprint = Blueprint("nail_sizes", __name__, url_prefix="/nail_sizes")

@nail_sizes_blueprint.route('/', methods=['GET'])
def get_nail_size_options():
    nail_size_options = NailSizeOption.query.all()
    return jsonify([option.to_dict() for option in nail_size_options]), 200

@nail_sizes_blueprint.route('/create', methods=['POST'])
def create_nail_size_option():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    nail_size_option = NailSizeOption(name=name, description=description)
    db.session.add(nail_size_option)
    db.session.commit()

    return jsonify(nail_size_option.to_dict()), 201