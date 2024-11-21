from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import app, db, Message, Conversation, User, FreightRequest
from datetime import datetime
from sqlalchemy import or_, and_

def create_system_message(conversation_id, freight_request_id, content, recipient_id):
    """Create a system-generated message."""
    message = Message(
        conversation_id=conversation_id,
        freight_request_id=freight_request_id,
        sender_id=0,  # System sender ID
        recipient_id=recipient_id,
        content=content,
        message_type='system',
        system_message=True,
        created_at=datetime.utcnow()
    )
    db.session.add(message)
    return message

def update_unread_count(user_id):
    """Update user's unread message count."""
    unread_count = Message.query.filter_by(
        recipient_id=user_id,
        read_at=None
    ).count()
    
    user = User.query.get(user_id)
    user.unread_messages = unread_count
    db.session.commit()

def init_messaging_routes(app):
    @app.route('/api/conversations', methods=['GET'])
    @jwt_required()
    def get_conversations():
        current_user_id = get_jwt_identity()
        
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 10, type=int)
            
            # Get conversations where user is either shipper or provider
            query = Conversation.query.filter(
                or_(
                    Conversation.shipper_id == current_user_id,
                    Conversation.provider_id == current_user_id
                )
            )
            
            # Filter out archived conversations based on user type
            query = query.filter(
                or_(
                    and_(
                        Conversation.shipper_id == current_user_id,
                        Conversation.shipper_archived == False
                    ),
                    and_(
                        Conversation.provider_id == current_user_id,
                        Conversation.provider_archived == False
                    )
                )
            )
            
            # Order by last message time
            conversations = query.order_by(Conversation.last_message_at.desc())\
                               .paginate(page=page, per_page=per_page, error_out=False)
            
            return jsonify({
                'conversations': [{
                    'id': conv.id,
                    'freight_request_id': conv.freight_request_id,
                    'shipper': {
                        'id': conv.shipper_id,
                        'company_name': User.query.get(conv.shipper_id).company_name
                    },
                    'provider': {
                        'id': conv.provider_id,
                        'company_name': User.query.get(conv.provider_id).company_name
                    },
                    'last_message_at': conv.last_message_at.isoformat(),
                    'unread_count': Message.query.filter_by(
                        conversation_id=conv.id,
                        recipient_id=current_user_id,
                        read_at=None
                    ).count()
                } for conv in conversations.items],
                'pagination': {
                    'total_items': conversations.total,
                    'total_pages': conversations.pages,
                    'current_page': page,
                    'per_page': per_page
                }
            }), 200
            
        except Exception as e:
            return jsonify({'error': 'Failed to fetch conversations', 'details': str(e)}), 500

    @app.route('/api/conversations/<int:freight_request_id>', methods=['POST'])
    @jwt_required()
    def start_conversation(freight_request_id):
        current_user_id = get_jwt_identity()
        
        # Get the freight request
        freight_request = FreightRequest.query.get(freight_request_id)
        if not freight_request:
            return jsonify({'error': 'Freight request not found'}), 404
        
        # Determine shipper and provider IDs
        current_user = User.query.get(current_user_id)
        if current_user.user_type == 'shipper':
            shipper_id = current_user_id
            provider_id = request.json.get('provider_id')
        else:
            shipper_id = freight_request.user_id
            provider_id = current_user_id
        
        # Check if conversation already exists
        existing_conv = Conversation.query.filter_by(
            freight_request_id=freight_request_id,
            shipper_id=shipper_id,
            provider_id=provider_id
        ).first()
        
        if existing_conv:
            return jsonify({
                'message': 'Conversation already exists',
                'conversation_id': existing_conv.id
            }), 200
        
        try:
            # Create new conversation
            conversation = Conversation(
                freight_request_id=freight_request_id,
                shipper_id=shipper_id,
                provider_id=provider_id
            )
            
            db.session.add(conversation)
            db.session.commit()
            
            # Create initial system message
            create_system_message(
                conversation.id,
                freight_request_id,
                f"Conversation started regarding freight request #{freight_request_id}",
                shipper_id if current_user_id != shipper_id else provider_id
            )
            
            db.session.commit()
            
            return jsonify({
                'message': 'Conversation created successfully',
                'conversation_id': conversation.id
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create conversation', 'details': str(e)}), 500

    @app.route('/api/conversations/<int:conversation_id>/messages', methods=['GET'])
    @jwt_required()
    def get_messages(conversation_id):
        current_user_id = get_jwt_identity()
        
        # Get the conversation
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Verify user is part of the conversation
        if current_user_id not in [conversation.shipper_id, conversation.provider_id]:
            return jsonify({'error': 'Not authorized to view these messages'}), 403
        
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            
            # Get messages
            messages = Message.query.filter_by(conversation_id=conversation_id)\
                                  .order_by(Message.created_at.desc())\
                                  .paginate(page=page, per_page=per_page, error_out=False)
            
            # Mark unread messages as read
            Message.query.filter_by(
                conversation_id=conversation_id,
                recipient_id=current_user_id,
                read_at=None
            ).update({'read_at': datetime.utcnow()})
            
            db.session.commit()
            
            # Update user's unread count
            update_unread_count(current_user_id)
            
            return jsonify({
                'messages': [{
                    'id': msg.id,
                    'sender_id': msg.sender_id,
                    'sender_name': User.query.get(msg.sender_id).company_name if not msg.system_message else 'System',
                    'content': msg.content,
                    'created_at': msg.created_at.isoformat(),
                    'read_at': msg.read_at.isoformat() if msg.read_at else None,
                    'message_type': msg.message_type,
                    'attachment_url': msg.attachment_url,
                    'system_message': msg.system_message
                } for msg in messages.items],
                'pagination': {
                    'total_items': messages.total,
                    'total_pages': messages.pages,
                    'current_page': page,
                    'per_page': per_page
                }
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to fetch messages', 'details': str(e)}), 500

    @app.route('/api/conversations/<int:conversation_id>/messages', methods=['POST'])
    @jwt_required()
    def send_message(conversation_id):
        current_user_id = get_jwt_identity()
        
        # Get the conversation
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Verify user is part of the conversation
        if current_user_id not in [conversation.shipper_id, conversation.provider_id]:
            return jsonify({'error': 'Not authorized to send messages in this conversation'}), 403
        
        data = request.get_json()
        
        # Validate message content
        if not data.get('content'):
            return jsonify({'error': 'Message content is required'}), 400
        
        try:
            # Create new message
            message = Message(
                conversation_id=conversation_id,
                freight_request_id=conversation.freight_request_id,
                sender_id=current_user_id,
                recipient_id=conversation.shipper_id if current_user_id == conversation.provider_id else conversation.provider_id,
                content=data['content'],
                message_type=data.get('message_type', 'text'),
                attachment_url=data.get('attachment_url')
            )
            
            # Update conversation last message time
            conversation.last_message_at = datetime.utcnow()
            
            # If conversation was archived by recipient, unarchive it
            if current_user_id == conversation.shipper_id:
                conversation.provider_archived = False
            else:
                conversation.shipper_archived = False
            
            db.session.add(message)
            db.session.commit()
            
            # Update recipient's unread count
            update_unread_count(message.recipient_id)
            
            return jsonify({
                'message': 'Message sent successfully',
                'message_id': message.id,
                'sent_at': message.created_at.isoformat()
            }), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to send message', 'details': str(e)}), 500

    @app.route('/api/conversations/<int:conversation_id>/archive', methods=['POST'])
    @jwt_required()
    def archive_conversation(conversation_id):
        current_user_id = get_jwt_identity()
        
        # Get the conversation
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Verify user is part of the conversation
        if current_user_id not in [conversation.shipper_id, conversation.provider_id]:
            return jsonify({'error': 'Not authorized to archive this conversation'}), 403
        
        try:
            # Archive conversation for the current user
            if current_user_id == conversation.shipper_id:
                conversation.shipper_archived = True
            else:
                conversation.provider_archived = True
            
            db.session.commit()
            
            return jsonify({
                'message': 'Conversation archived successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to archive conversation', 'details': str(e)}), 500
