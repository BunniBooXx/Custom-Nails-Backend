from flask import  request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from app .models import db, User, TokenBlocklist, datetime
from datetime import timezone
from flask import Blueprint

user_blueprint = Blueprint("user", __name__, url_prefix="/user")



@user_blueprint.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')

    if not (username and password and email):
        return jsonify({"message": "Missing required fields"}), 400

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"message": "Username already exists"}), 409

    user = User(username=username, password=password, email=email)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

from datetime import timedelta

@user_blueprint.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not (username and password):
        return jsonify({"message": "Username and password are required"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.compare_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    # Set token expiration time to 3 days
    expires = timedelta(days=3)

    # Generate access token with user object as identity and expiration time
    access_token = create_access_token(identity=user, expires_delta=expires)

    # Return token in headers with Bearer prefix
    response = jsonify(message="Login successful")
    response.headers['Authorization'] = f'Bearer {access_token}'
    return response, 200





@user_blueprint.put('/update/<int:user_id>/username')
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

from werkzeug.security import generate_password_hash

@user_blueprint.put('/update/<int:user_id>/password')
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

    # Hash the new password before updating
    hashed_password = generate_password_hash(password)

    user.password = hashed_password
    db.session.commit()

    return jsonify({"message": "Password updated"}), 200


# Similar functions for updating email and avatar_image can be defined.

@user_blueprint.put('/update/<int:user_id>/email')
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

@user_blueprint.put('/update/<int:user_id>/avatar')
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

from werkzeug.security import generate_password_hash

@user_blueprint.put('/update/<int:user_id>/all')
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
        # Hash the new password before updating
        hashed_password = generate_password_hash(password)
        user.password = hashed_password
    if email:
        user.email = email
    if avatar_image:
        user.avatar_image = avatar_image

    db.session.commit()

    return jsonify({"message": "User information updated", "data": user.to_response()}), 200




@user_blueprint.route('/delete/<int:user_id>', methods=['DELETE'])
@jwt_required()
def user_delete(user_id):
    current_user_id = get_jwt_identity()
    if current_user_id != user_id:
        return jsonify({"error": "Unauthorized: You can only delete your own account"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.delete()
    return jsonify({"message": "User deleted successfully"}), 200





@user_blueprint.route("/logout", methods=["DELETE"])
@jwt_required(verify_type=False)
def modify_token():
    token = get_jwt()
    jti = token["jti"]
    ttype = token["type"]
    now = datetime.now(timezone.utc)
    db.session.add(TokenBlocklist(jti=jti, type=ttype, created_at=now))
    db.session.commit()
    return jsonify(msg=f"{ttype.capitalize()} token successfully revoked")