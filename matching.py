from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db, FreightRequest, User, Quote
from datetime import datetime
import json

def calculate_match_score(request, provider):
    """Calculate a match score between a freight request and a provider."""
    score = 0
    
    # Convert provider's service areas and specialties from JSON string to list
    service_areas = json.loads(provider.service_areas or '[]')
    specialties = json.loads(provider.specialties or '[]')
    
    # Check if provider serves the origin/destination areas
    if request.origin in service_areas:
        score += 30
    if request.destination in service_areas:
        score += 30
        
    # Check if provider specializes in the freight type
    if request.freight_type in specialties:
        score += 20
        
    # Consider provider's rating
    score += min(provider.rating * 4, 20)  # Max 20 points for rating
    
    return score

def init_matching_routes(app):
    @app.route('/api/matching/available-requests', methods=['GET'])
    @jwt_required()
    def get_available_requests():
        current_user_id = get_jwt_identity()
        
        # Verify user is a provider
        provider = User.query.get(current_user_id)
        if not provider or provider.user_type != 'provider':
            return jsonify({'error': 'Only service providers can access matching'}), 403
            
        try:
            # Get query parameters for filtering
            freight_type = request.args.get('freight_type')
            min_weight = request.args.get('min_weight', type=float)
            max_weight = request.args.get('max_weight', type=float)
            
            # Base query for open freight requests
            query = FreightRequest.query.filter(
                FreightRequest.status.in_(['pending', 'quoted'])
            )
            
            # Apply filters
            if freight_type:
                query = query.filter_by(freight_type=freight_type)
            if min_weight:
                query = query.filter(FreightRequest.weight >= min_weight)
            if max_weight:
                query = query.filter(FreightRequest.weight <= max_weight)
                
            # Get all matching requests
            requests = query.all()
            
            # Calculate match scores and sort
            matched_requests = []
            for req in requests:
                # Skip requests where provider has already quoted
                if Quote.query.filter_by(freight_request_id=req.id, provider_id=current_user_id).first():
                    continue
                    
                score = calculate_match_score(req, provider)
                if score > 0:  # Only include if there's some match
                    matched_requests.append({
                        'request': {
                            'id': req.id,
                            'freight_type': req.freight_type,
                            'origin': req.origin,
                            'destination': req.destination,
                            'cargo_details': req.cargo_details,
                            'weight': req.weight,
                            'dimensions': req.dimensions,
                            'deadline': req.deadline.isoformat() if req.deadline else None,
                            'status': req.status,
                            'created_at': req.created_at.isoformat(),
                            'urgency': req.urgency,
                            'budget_range': req.budget_range
                        },
                        'match_score': score
                    })
            
            # Sort by match score (highest first)
            matched_requests.sort(key=lambda x: x['match_score'], reverse=True)
            
            return jsonify({
                'matched_requests': matched_requests
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch matching requests', 'details': str(e)}), 500

    @app.route('/api/matching/provider-profile', methods=['PUT'])
    @jwt_required()
    def update_provider_profile():
        current_user_id = get_jwt_identity()
        
        # Verify user is a provider
        provider = User.query.get(current_user_id)
        if not provider or provider.user_type != 'provider':
            return jsonify({'error': 'Only service providers can update matching profile'}), 403
            
        data = request.get_json()
        
        try:
            # Update service areas and specialties
            if 'service_areas' in data:
                provider.service_areas = json.dumps(data['service_areas'])
            if 'specialties' in data:
                provider.specialties = json.dumps(data['specialties'])
                
            db.session.commit()
            
            return jsonify({
                'message': 'Provider profile updated successfully',
                'service_areas': json.loads(provider.service_areas),
                'specialties': json.loads(provider.specialties)
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to update provider profile', 'details': str(e)}), 500
