from flask import request, jsonify, Blueprint
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import cross_origin
from datetime import timedelta
from app.models import db, User, TokenBlocklist
from app import app

user_blueprint = Blueprint("user", __name__, url_prefix="/user")


@user_blueprint.route('/', methods=['GET'])
@cross_origin()
def get_users():
    users = User.query.all()
    return jsonify([user.to_response() for user in users]), 200


def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.compare_password(password):
        return user
    return None

@user_blueprint.route('/signup', methods=['POST'])
@cross_origin()
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not (username and password and email):
        return jsonify({"message": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 409

    hashed_password = generate_password_hash(password)
    user = User(username=username, password=hashed_password, email=email)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201



@user_blueprint.route('/login', methods=['POST'])
@cross_origin(supports_credentials=True)
def login():
    app.logger.info("Login route called")
    
    data = request.json
    if data is None:
        app.logger.error("No data received")
        return jsonify({"message": "Invalid request"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    app.logger.info(f"Username: {username}")
    
    if not (username and password):
        app.logger.error("Username and/or password not provided")
        return jsonify({"message": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user or not user.compare_password(password):
        app.logger.error("Invalid credentials")
        return jsonify({"message": "Invalid credentials"}), 401

    # Create an access token with an expiration of 3 days
    access_token = create_access_token(identity=user.user_id, expires_delta=timedelta(days=3))
    refresh_token = create_refresh_token(identity=user.user_id)

    app.logger.info(f"Access token created for user id: {user.user_id}")

    # Create response
    response = jsonify(message="Login successful", access_token=access_token)
    response.set_cookie('refresh_token', refresh_token, httponly=True, secure=True, samesite='None')

    app.logger.info("Login successful")
    return response, 200

@user_blueprint.route('', methods=['GET'])
@cross_origin(supports_credentials=True)
@jwt_required()
def get_user_identity():
    user_id = get_jwt_identity()
    app.logger.info(f"Fetching user with ID: {user_id}")
    user = User.query.get(user_id)
    if user:
        return jsonify({
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email
        }), 200
    else:
        return jsonify({"message": "User not found"}), 404



@user_blueprint.route('/refresh', methods=['POST'])
@cross_origin(supports_credentials=True)
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user, expires_delta=timedelta(days=3))
    response = jsonify(access_token=access_token)
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response, 200



@user_blueprint.route('/protected', methods=['GET'])
@cross_origin()
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return jsonify(logged_in_as=user.username), 200



@user_blueprint.route('/update/<int:user_id>/username', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_username(user_id):
    current_user_id = get_jwt_identity()

    if current_user_id != user_id:
        return jsonify({"message": "Unauthorized: You can only update your own profile"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username is required"}), 400

    user.username = username
    db.session.commit()

    return jsonify({"message": "Username updated", "data": user.to_response()}), 200

@user_blueprint.route('/update/<int:user_id>/password', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_password(user_id):
    current_user_id = get_jwt_identity()

    if current_user_id != user_id:
        return jsonify({"message": "Unauthorized: You can only update your own profile"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    password = data.get("password")

    if not password:
        return jsonify({"message": "Password is required"}), 400

    hashed_password = generate_password_hash(password)
    user.password = hashed_password
    db.session.commit()

    return jsonify({"message": "Password updated"}), 200

@user_blueprint.route('/update/<int:user_id>/email', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_email(user_id):
    current_user_id = get_jwt_identity()

    if current_user_id != user_id:
        return jsonify({"message": "Unauthorized: You can only update your own profile"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"message": "Email is required"}), 400

    user.email = email
    db.session.commit()

    return jsonify({"message": "Email updated"}), 200

@user_blueprint.route('/update/<int:user_id>/avatar', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_avatar(user_id):
    current_user_id = get_jwt_identity()

    if current_user_id != user_id:
        return jsonify({"message": "Unauthorized: You can only update your own profile"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    avatar_image = data.get("avatar_image")

    if not avatar_image:
        return jsonify({"message": "Avatar image is required"}), 400

    user.avatar_image = avatar_image
    db.session.commit()

    return jsonify({"message": "Avatar image updated"}), 200

@user_blueprint.route('/get/<int:user_id>/avatar', methods=["GET"])
@cross_origin()
@jwt_required()
def get_avatar_image(user_id):
    user = User.query.get(user_id)
    if user:
        avatar_image = user.avatar_image or "default-avatar-image.jpg"
        return jsonify({
            "avatar_image": avatar_image
        }), 200
    else:
        return jsonify({"message": "User not found"}), 404

@user_blueprint.route('/update/<int:user_id>/all', methods=['PUT'])
@cross_origin()
@jwt_required()
def update_user_info(user_id):
    current_user_id = get_jwt_identity()

    if current_user_id != user_id:
        return jsonify({"message": "Unauthorized: You can only update your own profile"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    data = request.json
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    avatar_image = data.get("avatar_image")

    if username:
        user.username = username
    if password:
        hashed_password = generate_password_hash(password)
        user.password = hashed_password
    if email:
        user.email = email
    if avatar_image:
        user.avatar_image = avatar_image

    db.session.commit()

    return jsonify({"message": "User information updated", "data": user.to_response()}), 200

@user_blueprint.route('/logout', methods=["DELETE"])
@cross_origin()
@jwt_required(verify_type=False)
def modify_token():
    token = get_jwt()
    jti = token["jti"]
    ttype = token["type"]
    
    current_user_id = get_jwt_identity()
    user_id = current_user_id if current_user_id else None
    
    db.session.add(TokenBlocklist(jti=jti, type=ttype, user_id=user_id))
    db.session.commit()
    return jsonify(msg=f"{ttype.capitalize()} token successfully revoked")
