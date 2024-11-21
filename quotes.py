from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db, Quote, FreightRequest, User
from datetime import datetime, timedelta

def init_quote_routes(app):
    @app.route('/api/quotes/<int:request_id>', methods=['POST'])
    @jwt_required()
    def submit_quote(request_id):
        current_user_id = get_jwt_identity()
        
        # Verify user is a provider
        provider = User.query.get(current_user_id)
        if not provider or provider.user_type != 'provider':
            return jsonify({'error': 'Only service providers can submit quotes'}), 403
        
        # Check if freight request exists and is still open
        freight_request = FreightRequest.query.get(request_id)
        if not freight_request:
            return jsonify({'error': 'Freight request not found'}), 404
        if freight_request.status not in ['pending', 'quoted']:
            return jsonify({'error': 'Freight request is no longer accepting quotes'}), 400
            
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['price', 'estimated_delivery_date']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        try:
            # Set quote validity period (default 48 hours)
            valid_until = datetime.utcnow() + timedelta(hours=48)
            
            # Create new quote
            new_quote = Quote(
                freight_request_id=request_id,
                provider_id=current_user_id,
                price=data['price'],
                estimated_delivery_date=datetime.fromisoformat(data['estimated_delivery_date']),
                description=data.get('description', ''),
                status='pending',
                valid_until=valid_until,
                terms_conditions=data.get('terms_conditions', ''),
                insurance_coverage=data.get('insurance_coverage', 0.0)
            )
            
            db.session.add(new_quote)
            
            # Update freight request status if this is the first quote
            if freight_request.status == 'pending':
                freight_request.status = 'quoted'
                
            db.session.commit()
            
            return jsonify({
                'message': 'Quote submitted successfully',
                'quote_id': new_quote.id,
                'valid_until': valid_until.isoformat()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to submit quote', 'details': str(e)}), 500

    @app.route('/api/quotes/<int:request_id>', methods=['GET'])
    @jwt_required()
    def get_quotes(request_id):
        current_user_id = get_jwt_identity()
        
        # Get the freight request
        freight_request = FreightRequest.query.get(request_id)
        if not freight_request:
            return jsonify({'error': 'Freight request not found'}), 404
            
        # Verify user is either the shipper or a provider who submitted a quote
        if (freight_request.user_id != current_user_id and 
            not Quote.query.filter_by(freight_request_id=request_id, provider_id=current_user_id).first()):
            return jsonify({'error': 'Not authorized to view these quotes'}), 403
            
        try:
            quotes = Quote.query.filter_by(freight_request_id=request_id).all()
            
            return jsonify({
                'quotes': [{
                    'id': quote.id,
                    'provider_id': quote.provider_id,
                    'provider_name': quote.provider.company_name,
                    'provider_rating': quote.provider.rating,
                    'price': quote.price,
                    'estimated_delivery_date': quote.estimated_delivery_date.isoformat(),
                    'description': quote.description,
                    'status': quote.status,
                    'valid_until': quote.valid_until.isoformat(),
                    'insurance_coverage': quote.insurance_coverage
                } for quote in quotes]
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch quotes', 'details': str(e)}), 500

    @app.route('/api/quotes/<int:quote_id>/accept', methods=['POST'])
    @jwt_required()
    def accept_quote(quote_id):
        current_user_id = get_jwt_identity()
        
        # Get the quote
        quote = Quote.query.get(quote_id)
        if not quote:
            return jsonify({'error': 'Quote not found'}), 404
            
        # Get the freight request
        freight_request = FreightRequest.query.get(quote.freight_request_id)
        
        # Verify user is the shipper
        if freight_request.user_id != current_user_id:
            return jsonify({'error': 'Only the shipper can accept quotes'}), 403
            
        # Verify quote is still valid
        if quote.valid_until < datetime.utcnow():
            return jsonify({'error': 'Quote has expired'}), 400
            
        try:
            # Update quote status
            quote.status = 'accepted'
            
            # Update freight request
            freight_request.status = 'in_progress'
            freight_request.selected_quote_id = quote.id
            
            # Reject all other quotes
            Quote.query.filter_by(freight_request_id=freight_request.id)\
                      .filter(Quote.id != quote_id)\
                      .update({'status': 'rejected'})
            
            db.session.commit()
            
            return jsonify({
                'message': 'Quote accepted successfully',
                'freight_request_status': 'in_progress'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to accept quote', 'details': str(e)}), 500
