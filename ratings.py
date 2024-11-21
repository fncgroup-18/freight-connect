from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db, Rating, FreightRequest, User, Quote
from sqlalchemy import func
from datetime import datetime

def update_provider_rating(provider_id):
    """Update the provider's average rating."""
    try:
        # Calculate new average rating
        avg_rating = db.session.query(func.avg(Rating.rating))\
            .filter(Rating.provider_id == provider_id)\
            .scalar() or 0.0
        
        # Count total ratings
        total_ratings = Rating.query.filter_by(provider_id=provider_id).count()
        
        # Update provider
        provider = User.query.get(provider_id)
        provider.rating = float(avg_rating)
        provider.total_ratings = total_ratings
        db.session.commit()
        
        return True
    except Exception:
        db.session.rollback()
        return False

def init_rating_routes(app):
    @app.route('/api/ratings/<int:request_id>', methods=['POST'])
    @jwt_required()
    def submit_rating(request_id):
        current_user_id = get_jwt_identity()
        
        # Get the freight request
        freight_request = FreightRequest.query.get(request_id)
        if not freight_request:
            return jsonify({'error': 'Freight request not found'}), 404
        
        # Verify user is the shipper
        if freight_request.user_id != current_user_id:
            return jsonify({'error': 'Only the shipper can submit ratings'}), 403
        
        # Verify request is completed
        if freight_request.status != 'completed':
            return jsonify({'error': 'Can only rate completed freight requests'}), 400
        
        # Get the selected quote/provider
        if not freight_request.selected_quote_id:
            return jsonify({'error': 'No provider was selected for this request'}), 400
        
        quote = Quote.query.get(freight_request.selected_quote_id)
        provider_id = quote.provider_id
        
        # Check if already rated
        existing_rating = Rating.query.filter_by(
            freight_request_id=request_id,
            shipper_id=current_user_id
        ).first()
        
        if existing_rating:
            return jsonify({'error': 'You have already rated this service'}), 400
        
        data = request.get_json()
        
        # Validate rating
        rating_value = data.get('rating')
        if not rating_value or not isinstance(rating_value, int) or rating_value < 1 or rating_value > 5:
            return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
        
        try:
            # Create new rating
            new_rating = Rating(
                freight_request_id=request_id,
                provider_id=provider_id,
                shipper_id=current_user_id,
                rating=rating_value,
                review=data.get('review', ''),
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_rating)
            db.session.commit()
            
            # Update provider's average rating
            if not update_provider_rating(provider_id):
                return jsonify({'error': 'Failed to update provider rating'}), 500
            
            return jsonify({
                'message': 'Rating submitted successfully',
                'rating_id': new_rating.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to submit rating', 'details': str(e)}), 500

    @app.route('/api/ratings/provider/<int:provider_id>', methods=['GET'])
    @jwt_required()
    def get_provider_ratings(provider_id):
        try:
            # Verify provider exists
            provider = User.query.get(provider_id)
            if not provider or provider.user_type != 'provider':
                return jsonify({'error': 'Provider not found'}), 404
            
            # Get query parameters for filtering
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            min_rating = request.args.get('min_rating', type=int)
            
            # Base query
            query = Rating.query.filter_by(provider_id=provider_id)
            
            # Apply rating filter if specified
            if min_rating:
                query = query.filter(Rating.rating >= min_rating)
            
            # Get paginated results
            ratings = query.order_by(Rating.created_at.desc())\
                         .paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                'provider': {
                    'id': provider.id,
                    'company_name': provider.company_name,
                    'average_rating': provider.rating,
                    'total_ratings': provider.total_ratings
                },
                'ratings': [{
                    'id': rating.id,
                    'rating': rating.rating,
                    'review': rating.review,
                    'created_at': rating.created_at.isoformat(),
                    'freight_request_id': rating.freight_request_id
                } for rating in ratings.items],
                'pagination': {
                    'total_items': ratings.total,
                    'total_pages': ratings.pages,
                    'current_page': ratings.page,
                    'per_page': per_page
                }
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch ratings', 'details': str(e)}), 500

    @app.route('/api/ratings/stats/provider/<int:provider_id>', methods=['GET'])
    def get_provider_rating_stats(provider_id):
        try:
            # Verify provider exists
            provider = User.query.get(provider_id)
            if not provider or provider.user_type != 'provider':
                return jsonify({'error': 'Provider not found'}), 404
            
            # Get rating distribution
            rating_distribution = db.session.query(
                Rating.rating,
                func.count(Rating.id).label('count')
            ).filter_by(provider_id=provider_id)\
             .group_by(Rating.rating)\
             .all()
            
            # Convert to dictionary
            distribution = {i: 0 for i in range(1, 6)}  # Initialize all ratings to 0
            for rating, count in rating_distribution:
                distribution[rating] = count
            
            # Calculate rating percentages
            total_ratings = sum(distribution.values())
            rating_percentages = {
                rating: (count / total_ratings * 100 if total_ratings > 0 else 0)
                for rating, count in distribution.items()
            }
            
            return jsonify({
                'provider': {
                    'id': provider.id,
                    'company_name': provider.company_name,
                    'average_rating': provider.rating,
                    'total_ratings': provider.total_ratings
                },
                'distribution': distribution,
                'percentages': rating_percentages
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch rating stats', 'details': str(e)}), 500

    @app.route('/api/ratings/<int:rating_id>', methods=['GET'])
    @jwt_required()
    def get_rating_details(rating_id):
        try:
            rating = Rating.query.get(rating_id)
            if not rating:
                return jsonify({'error': 'Rating not found'}), 404
            
            # Get related freight request details
            freight_request = FreightRequest.query.get(rating.freight_request_id)
            
            return jsonify({
                'rating': {
                    'id': rating.id,
                    'rating': rating.rating,
                    'review': rating.review,
                    'created_at': rating.created_at.isoformat(),
                },
                'freight_request': {
                    'id': freight_request.id,
                    'freight_type': freight_request.freight_type,
                    'origin': freight_request.origin,
                    'destination': freight_request.destination,
                    'completed_at': freight_request.created_at.isoformat()
                },
                'provider': {
                    'id': rating.provider_id,
                    'company_name': User.query.get(rating.provider_id).company_name
                }
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch rating details', 'details': str(e)}), 500
