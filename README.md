# FreightConnect - Logistics Marketplace Platform

FreightConnect is a comprehensive web platform that connects businesses with logistics service providers through intelligent matching and communication capabilities.

## Features

- User Authentication (JWT-based)
- Freight Request Management
- Quote System
- Provider-Shipper Messaging
- Rating System
- Service Provider Matching

## Tech Stack

- Backend: Flask (Python)
- Database: SQLAlchemy with SQLite (development)
- Authentication: JWT
- Password Security: BCrypt

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/freight-connect.git
cd freight-connect
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory:
```
SECRET_KEY=your-secret-key-replace-in-production
JWT_SECRET_KEY=your-jwt-secret-key-replace-in-production
DATABASE_URL=sqlite:///freight_connect.db
FLASK_ENV=development
```

5. Initialize the database:
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

6. Run the application:
```bash
python app.py
```

The server will start at `http://localhost:5000`.

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

### Freight Requests

- `POST /api/freight-requests` - Create a new freight request
- `GET /api/freight-requests` - List freight requests
- `GET /api/freight-requests/<id>` - Get freight request details

### Quotes

- `POST /api/quotes` - Submit a quote
- `GET /api/quotes` - List quotes
- `GET /api/quotes/<id>` - Get quote details

### Messaging

- `POST /api/conversations/<freight_request_id>` - Start conversation
- `GET /api/conversations` - List conversations
- `GET /api/conversations/<conversation_id>/messages` - Retrieve messages
- `POST /api/conversations/<conversation_id>/messages` - Send message
- `POST /api/conversations/<conversation_id>/archive` - Archive conversation

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
