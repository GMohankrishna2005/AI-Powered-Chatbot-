"""
Flask REST API for AI-Powered Chatbot.
Main application entry point with POST /chat endpoint.
Integrates NLP chatbot with SQLite database for conversation logging.
"""

import logging
import uuid
import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from datetime import datetime

from chatbot import create_chatbot
from database import ChatbotDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Enable CORS for all routes
CORS(app)

# Initialize chatbot and database
try:
    chatbot = create_chatbot()
    logger.info("Chatbot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize chatbot: {e}")
    chatbot = None

try:
    db = ChatbotDatabase("chatbot.db")
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")
    db = None


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify API is running.
    
    Returns:
        JSON: Status and timestamp
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "AI-Powered Chatbot API"
    }), 200


@app.route('/chat', methods=['POST'])
def chat():
    """
    Main chatbot endpoint for handling user messages.
    
    Request JSON:
        {
            "message": "user question",
            "session_id": "optional-session-id"
        }
    
    Response JSON:
        {
            "response": "chatbot answer",
            "confidence": 0.85,
            "type": "faq_match",
            "conversation_id": 123,
            "timestamp": "2024-01-15T10:30:00"
        }
    
    Returns:
        JSON: Chatbot response with metadata
    """
    
    # Validate request method and content type
    if request.method != 'POST':
        return jsonify({"error": "Method not allowed"}), 405
    
    # Parse JSON request
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON request"}), 400
    except Exception as e:
        logger.warning(f"JSON parsing error: {e}")
        return jsonify({"error": "Malformed JSON"}), 400
    
    # Validate and sanitize input
    user_message = data.get('message', '').strip()
    session_id = data.get('session_id', str(uuid.uuid4()))
    
    if not user_message:
        return jsonify({"error": "Message field is required and cannot be empty"}), 400
    
    if len(user_message) > 5000:
        return jsonify({"error": "Message exceeds maximum length of 5000 characters"}), 400
    
    try:
        # Generate chatbot response
        if chatbot is None:
            return jsonify({
                "error": "Chatbot service unavailable",
                "response": "Service temporarily unavailable. Please try again later."
            }), 503
        
        bot_response_data = chatbot.generate_response(user_message)
        bot_response = bot_response_data.get('response', 'Unable to generate response')
        confidence = bot_response_data.get('confidence', 0.0)
        response_type = bot_response_data.get('type', 'unknown')
        
        # Save to database
        conversation_id = None
        if db:
            try:
                conversation_id = db.save_conversation(
                    user_message=user_message,
                    bot_response=bot_response,
                    session_id=session_id
                )
            except Exception as db_error:
                logger.error(f"Database save error: {db_error}")
                # Continue even if database fails
        
        # Build response
        response = {
            "response": bot_response,
            "confidence": round(confidence, 2),
            "type": response_type,
            "conversation_id": conversation_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Chat request processed - Session: {session_id}, Type: {response_type}")
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "response": "An unexpected error occurred. Please try again."
        }), 500


@app.route('/history', methods=['GET'])
def get_history():
    """
    Retrieve conversation history.
    
    Query Parameters:
        limit: Number of records to retrieve (default: 10, max: 100)
        session_id: Optional session filter
    
    Returns:
        JSON: List of past conversations
    """
    try:
        limit = request.args.get('limit', default=10, type=int)
        session_id = request.args.get('session_id', default=None, type=str)
        
        # Validate limit
        if limit < 1 or limit > 100:
            limit = 10
        
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        
        history = db.get_conversation_history(limit=limit, session_id=session_id)
        total = db.get_total_conversations()
        
        return jsonify({
            "conversations": history,
            "total_stored": total,
            "returned": len(history),
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return jsonify({"error": "Failed to retrieve conversation history"}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get chatbot statistics.
    
    Returns:
        JSON: Statistics about conversations
    """
    try:
        if db is None:
            return jsonify({"error": "Database unavailable"}), 503
        
        total_conversations = db.get_total_conversations()
        
        return jsonify({
            "total_conversations": total_conversations,
            "status": "operational",
            "timestamp": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving stats: {e}")
        return jsonify({"error": "Failed to retrieve statistics"}), 500


@app.route('/', methods=['GET'])
def index():
    """Welcome endpoint - serve HTML interface."""
    try:
        return send_file('index.html', mimetype='text/html')
    except Exception as e:
        logger.error(f"Error serving index.html: {e}")
        return jsonify({
            "name": "AI-Powered Chatbot API",
            "version": "1.0.0",
            "description": "REST API for customer support chatbot with NLP",
            "endpoints": {
                "GET /health": "Health check",
                "POST /chat": "Send message and get response",
                "GET /history": "Retrieve conversation history",
                "GET /stats": "Get chatbot statistics"
            },
            "usage": {
                "POST /chat": {
                    "request": {
                        "message": "Your question",
                        "session_id": "optional-session-id"
                    },
                    "example": "curl -X POST http://localhost:5000/chat -H 'Content-Type: application/json' -d '{\"message\": \"What are your hours?\"}'"
                }
            }
        }), 200


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    logger.info("Starting AI-Powered Chatbot Flask Server")
    logger.info("Server running at http://127.0.0.1:5000")
    logger.info("Available endpoints: /health, /chat, /history, /stats")
    
    # Run Flask app on Windows-friendly settings
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,  # Set to False for production
        use_reloader=False,  # Disable reloader for Windows stability
        threaded=True  # Enable threading for concurrent requests
    )
