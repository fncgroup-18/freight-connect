from datetime import datetime
from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    company_name = db.Column(db.String(100))
    user_type = db.Column(db.String(20))  # 'shipper' or 'provider'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    freight_requests = db.relationship('FreightRequest', backref='user', lazy=True)
    quotes_submitted = db.relationship('Quote', backref='provider', lazy=True)
    rating = db.Column(db.Float, default=0.0)
    total_ratings = db.Column(db.Integer, default=0)
    service_areas = db.Column(db.String(500))  # JSON string of service areas
    specialties = db.Column(db.String(500))  # JSON string of freight specialties
    messages_sent = db.relationship('Message', backref='sender', lazy=True, foreign_keys='Message.sender_id')
    messages_received = db.relationship('Message', backref='recipient', lazy=True, foreign_keys='Message.recipient_id')
    unread_messages = db.Column(db.Integer, default=0)

class FreightRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freight_type = db.Column(db.String(50))  # road, air, sea, rail
    origin = db.Column(db.String(200))
    destination = db.Column(db.String(200))
    cargo_details = db.Column(db.Text)
    weight = db.Column(db.Float)
    dimensions = db.Column(db.String(100))
    deadline = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # pending, quoted, in_progress, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quotes = db.relationship('Quote', backref='freight_request', lazy=True)
    selected_quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=True)
    urgency = db.Column(db.String(20))  # normal, urgent, very_urgent
    budget_range = db.Column(db.String(50))  # Optional budget range
    messages = db.relationship('Message', backref='freight_request', lazy=True)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freight_request_id = db.Column(db.Integer, db.ForeignKey('freight_request.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    estimated_delivery_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20))  # pending, accepted, rejected, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=False)
    terms_conditions = db.Column(db.Text)
    insurance_coverage = db.Column(db.Float)  # Insurance coverage amount
    requests_selected = db.relationship('FreightRequest', backref='selected_quote', lazy=True,
                                      foreign_keys=[FreightRequest.selected_quote_id])

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freight_request_id = db.Column(db.Integer, db.ForeignKey('freight_request.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    shipper_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 rating
    review = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    freight_request_id = db.Column(db.Integer, db.ForeignKey('freight_request.id'), nullable=False)
    shipper_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True)
    shipper_archived = db.Column(db.Boolean, default=False)
    provider_archived = db.Column(db.Boolean, default=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    freight_request_id = db.Column(db.Integer, db.ForeignKey('freight_request.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    message_type = db.Column(db.String(20))  # 'text', 'quote_update', 'status_update', etc.
    attachment_url = db.Column(db.String(500))  # For file attachments
    system_message = db.Column(db.Boolean, default=False)  # For automated system messages
