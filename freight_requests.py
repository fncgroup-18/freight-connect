from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import FreightRequest, User
from datetime import datetime

def init_freight_routes(app):
    @app.route('/api/freight-requests', methods=['POST'])
    @jwt_required()
    def create_freight_request():
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or user.user_type != 'shipper':
            return jsonify({'error': 'Only shippers can create freight requests'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['freight_type', 'origin', 'destination', 'cargo_details']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        try:
            new_request = FreightRequest(
                user_id=current_user_id,
                freight_type=data['freight_type'],
                origin=data['origin'],
                destination=data['destination'],
                cargo_details=data['cargo_details'],
                weight=data.get('weight'),
                dimensions=data.get('dimensions'),
                deadline=datetime.fromisoformat(data['deadline']) if 'deadline' in data else None,
                status='pending',
                urgency=data.get('urgency', 'normal'),
                budget_range=data.get('budget_range')
            )
            
            db.session.add(new_request)
            db.session.commit()
            
            return jsonify({
                'message': 'Freight request created successfully',
                'freight_request': {
                    'id': new_request.id,
                    'freight_type': new_request.freight_type,
                    'origin': new_request.origin,
                    'destination': new_request.destination,
                    'status': new_request.status
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create freight request', 'details': str(e)}), 500

    @app.route('/api/freight-requests', methods=['GET'])
    @jwt_required()
    def get_freight_requests():
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # Filter based on user type
            if user.user_type == 'shipper':
                # Shippers see their own requests
                query = FreightRequest.query.filter_by(user_id=current_user_id)
            else:
                # Providers see all available requests except completed ones
                query = FreightRequest.query.filter(FreightRequest.status != 'completed')
            
            # Apply additional filters
            status = request.args.get('status')
            if status:
                query = query.filter_by(status=status)
            
            freight_type = request.args.get('freight_type')
            if freight_type:
                query = query.filter_by(freight_type=freight_type)
            
            # Order by creation date, newest first
            query = query.order_by(FreightRequest.created_at.desc())
            
            # Paginate results
            pagination = query.paginate(page=page, per_page=per_page)
            
            freight_requests = [{
                'id': fr.id,
                'freight_type': fr.freight_type,
                'origin': fr.origin,
                'destination': fr.destination,
                'cargo_details': fr.cargo_details,
                'weight': fr.weight,
                'dimensions': fr.dimensions,
                'deadline': fr.deadline.isoformat() if fr.deadline else None,
                'status': fr.status,
                'created_at': fr.created_at.isoformat(),
                'urgency': fr.urgency,
                'budget_range': fr.budget_range,
                'quotes_count': len(fr.quotes)
            } for fr in pagination.items]
            
            return jsonify({
                'freight_requests': freight_requests,
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch freight requests', 'details': str(e)}), 500

    @app.route('/api/freight-requests/<int:request_id>', methods=['GET'])
    @jwt_required()
    def get_freight_request(request_id):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        try:
            freight_request = FreightRequest.query.get(request_id)
            
            if not freight_request:
                return jsonify({'error': 'Freight request not found'}), 404
            
            # Check if user has permission to view this request
            if user.user_type == 'shipper' and freight_request.user_id != current_user_id:
                return jsonify({'error': 'Not authorized to view this request'}), 403
            
            response = {
                'id': freight_request.id,
                'freight_type': freight_request.freight_type,
                'origin': freight_request.origin,
                'destination': freight_request.destination,
                'cargo_details': freight_request.cargo_details,
                'weight': freight_request.weight,
                'dimensions': freight_request.dimensions,
                'deadline': freight_request.deadline.isoformat() if freight_request.deadline else None,
                'status': freight_request.status,
                'created_at': freight_request.created_at.isoformat(),
                'urgency': freight_request.urgency,
                'budget_range': freight_request.budget_range,
                'shipper': {
                    'id': freight_request.user.id,
                    'company_name': freight_request.user.company_name
                },
                'quotes': [{
                    'id': quote.id,
                    'provider_id': quote.provider_id,
                    'provider_name': quote.provider.company_name,
                    'price': quote.price,
                    'status': quote.status,
                    'created_at': quote.created_at.isoformat()
                } for quote in freight_request.quotes] if user.user_type == 'shipper' or freight_request.user_id == current_user_id else []
            }
            
            return jsonify(response), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch freight request', 'details': str(e)}), 500
