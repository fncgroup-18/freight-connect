from flask import Flask, jsonify
from datetime import timedelta
import os
from dotenv import load_dotenv
from extensions import db, jwt, bcrypt, cors

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///freight_connect.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app)

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'healthy'})

    # Import models and routes
    with app.app_context():
        from models import User, FreightRequest, Quote, Rating, Conversation, Message
        from auth import init_auth_routes
        from freight_requests import init_freight_routes
        from quotes import init_quote_routes
        from matching import init_matching_routes
        from ratings import init_rating_routes
        from messaging import init_messaging_routes

        # Initialize routes
        init_auth_routes(app)
        init_freight_routes(app)
        init_quote_routes(app)
        init_matching_routes(app)
        init_rating_routes(app)
        init_messaging_routes(app)

        # Create database tables
        db.create_all()

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
