from flask import jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from extensions import db, bcrypt
from models import User

def init_auth_routes(app):
    bcrypt.init_app(app)

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'company_name', 'user_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate user type
        if data['user_type'] not in ['shipper', 'provider']:
            return jsonify({'error': 'Invalid user type. Must be either "shipper" or "provider"'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        try:
            # Hash password
            hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
            
            # Create new user
            new_user = User(
                email=data['email'],
                password=hashed_password,
                company_name=data['company_name'],
                user_type=data['user_type'],
                service_areas=data.get('service_areas'),
                specialties=data.get('specialties')
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            # Create access token
            access_token = create_access_token(identity=new_user.id)
            
            return jsonify({
                'message': 'Registration successful',
                'access_token': access_token,
                'user': {
                    'id': new_user.id,
                    'email': new_user.email,
                    'company_name': new_user.company_name,
                    'user_type': new_user.user_type
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Registration failed', 'details': str(e)}), 500

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
        
        try:
            # Find user by email
            user = User.query.filter_by(email=data['email']).first()
            
            # Check if user exists and password is correct
            if user and bcrypt.check_password_hash(user.password, data['password']):
                # Create access token
                access_token = create_access_token(identity=user.id)
                
                return jsonify({
                    'message': 'Login successful',
                    'access_token': access_token,
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'company_name': user.company_name,
                        'user_type': user.user_type
                    }
                }), 200
            else:
                return jsonify({'error': 'Invalid email or password'}), 401
                
        except Exception as e:
            return jsonify({'error': 'Login failed', 'details': str(e)}), 500

    @app.route('/api/auth/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        current_user_id = get_jwt_identity()
        
        try:
            user = User.query.get(current_user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'company_name': user.company_name,
                    'user_type': user.user_type,
                    'rating': user.rating,
                    'total_ratings': user.total_ratings,
                    'service_areas': user.service_areas,
                    'specialties': user.specialties,
                    'unread_messages': user.unread_messages
                }
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to get user info', 'details': str(e)}), 500
