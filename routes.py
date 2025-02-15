import os
import jwt
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from models import db, Duration, Media, User, Token
from flask import Blueprint, request, jsonify, current_app

# Create a Blueprint
api = Blueprint('api', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_token(user):
    # Check if a valid token already exists
    existing_token = Token.query.filter_by(user_id=user.id).order_by(Token.id.desc()).first()

    if existing_token:
        try:
            # Decode token to check expiration
            payload = jwt.decode(existing_token.token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return existing_token.token  # Return existing token if it's still valid
        except jwt.ExpiredSignatureError:
            pass  # Token expired, proceed to generate a new one

    # Generate a new token if none exists or the existing one is expired
    expiration = datetime.utcnow() + timedelta(hours=1)
    token = jwt.encode({'user_id': user.id, 'exp': expiration}, current_app.config['SECRET_KEY'], algorithm='HS256')

    # Store the new token in the database
    new_token = Token(user_id=user.id, token=token)
    db.session.add(new_token)
    db.session.commit()

    return token

# --------------- Authentication Routes --------------

@api.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    new_user = User(email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@api.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()

    if user and user.check_password(password):
        token = generate_token(user)
        return jsonify({'access_token': token, "user_id":user.id }), 200
    else:
        return jsonify({'message': 'Invalid email or password'}), 401

# --------------- Duration Routes --------------
@api.route('/duration/user/<int:user_id>', methods=['GET'])
def get_duration_by_user(user_id):  
    today = datetime.today().date()

    duration = Duration.query.filter_by(user_id=user_id, date=today).first()  # Get only one record
    if not duration:
        new_duration = Duration(
            user_id=user_id,
            total_time='00:00:00',
            date=today
        )
        db.session.add(new_duration)
        db.session.commit()

        return jsonify({
            "success":True,
            "id": new_duration.id,
            "user_id": new_duration.user_id,
            "total_time": new_duration.total_time,
            "date": new_duration.date.strftime('%Y-%m-%d')
        })
        
    return jsonify({
        "success":True,
        "id": duration.id,
        "user_id": duration.user_id,
        "total_time": duration.total_time,
        "date": duration.date.strftime('%Y-%m-%d')
    })

@api.route('/duration/update', methods=['POST'])
def update_duration():
    """Updates the duration for a given duration_id and user_id."""
    data = request.get_json()

    # Validate required fields
    duration_id = data.get('duration_id')
    user_id = data.get('user_id')  # Ensure user_id is checked
    new_total_time = data.get('total_time')

    if not duration_id or not user_id or not new_total_time:
        return jsonify({"error": "Missing required fields"}), 400

    # Fetch duration and ensure it belongs to the user
    duration = Duration.query.filter_by(id=duration_id, user_id=user_id).first()
    if not duration:
        return jsonify({"error": "Duration not found or doesn't belong to user"}), 404

    # Update total time
    duration.total_time = new_total_time
    db.session.commit()

    return jsonify({"message": "Duration updated successfully", "new_total_time": new_total_time})


# ------------------- Media Routes -------------------
@api.route('/media', methods=['POST'])
def add_media():
    """Handle media upload and store in database"""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id')
    key_presses = request.form.get('key_log')
    number_of_input = request.form.get('key_counts')
    
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)  # Save the file to the media folder

        # Store metadata in the database
        new_media = Media(
            user_id=user_id,
            total_input=key_presses,
            number_of_input=number_of_input,
            image_src=filepath  # Store the file path in the database
        )
        db.session.add(new_media)
        db.session.commit()

        return jsonify({"message": "Media added successfully", "id": new_media.id, "image_src": filepath}), 201
    else:
        return jsonify({"error": "Invalid file format"}), 400