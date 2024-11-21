from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db, FreightRequest
from datetime import datetime

def init_freight_routes(app):
    @app.route('/api/freight-requests', methods=['POST'])
    @jwt_required()
    def create_freight_request():
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['freight_type', 'origin', 'destination', 'cargo_details']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Validate freight type
        valid_freight_types = ['road', 'air', 'sea', 'rail']
        if data['freight_type'] not in valid_freight_types:
            return jsonify({'error': 'Invalid freight type'}), 400
        
        try:
            # Create new freight request
            new_request = FreightRequest(
                user_id=current_user_id,
                freight_type=data['freight_type'],
                origin=data['origin'],
                destination=data['destination'],
                cargo_details=data['cargo_details'],
                weight=data.get('weight'),
                dimensions=data.get('dimensions'),
                deadline=datetime.fromisoformat(data['deadline']) if data.get('deadline') else None,
                status='pending'
            )
            
            db.session.add(new_request)
            db.session.commit()
            
            return jsonify({
                'message': 'Freight request created successfully',
                'request_id': new_request.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create freight request', 'details': str(e)}), 500

    @app.route('/api/freight-requests', methods=['GET'])
    @jwt_required()
    def get_freight_requests():
        current_user_id = get_jwt_identity()
        
        # Get query parameters for filtering
        freight_type = request.args.get('freight_type')
        status = request.args.get('status')
        
        # Base query
        query = FreightRequest.query
        
        # Apply filters
        if freight_type:
            query = query.filter_by(freight_type=freight_type)
        if status:
            query = query.filter_by(status=status)
            
        # Get requests
        try:
            requests = query.all()
            
            return jsonify({
                'freight_requests': [{
                    'id': req.id,
                    'freight_type': req.freight_type,
                    'origin': req.origin,
                    'destination': req.destination,
                    'cargo_details': req.cargo_details,
                    'weight': req.weight,
                    'dimensions': req.dimensions,
                    'deadline': req.deadline.isoformat() if req.deadline else None,
                    'status': req.status,
                    'created_at': req.created_at.isoformat()
                } for req in requests]
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch freight requests', 'details': str(e)}), 500

    @app.route('/api/freight-requests/<int:request_id>', methods=['GET'])
    @jwt_required()
    def get_freight_request(request_id):
        try:
            request = FreightRequest.query.get(request_id)
            
            if not request:
                return jsonify({'error': 'Freight request not found'}), 404
                
            return jsonify({
                'id': request.id,
                'freight_type': request.freight_type,
                'origin': request.origin,
                'destination': request.destination,
                'cargo_details': request.cargo_details,
                'weight': request.weight,
                'dimensions': request.dimensions,
                'deadline': request.deadline.isoformat() if request.deadline else None,
                'status': request.status,
                'created_at': request.created_at.isoformat()
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch freight request', 'details': str(e)}), 500
