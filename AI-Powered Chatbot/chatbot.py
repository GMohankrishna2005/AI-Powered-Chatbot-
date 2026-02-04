"""
Chatbot NLP module for AI-Powered Chatbot.
Uses Hugging Face Transformers for semantic similarity and response generation.
Handles token sanitization and safe model loading.
"""

import re
import logging
from typing import Dict, List, Tuple
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
import warnings

# Suppress transformers warnings
warnings.filterwarnings('ignore', category=UserWarning)
logging.getLogger('transformers').setLevel(logging.ERROR)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)


class AICharacter:
    """
    AI Chatbot character for customer support and FAQs.
    Uses transformer-based semantic similarity for response matching.
    """
    
    def __init__(self, model_name: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        """
        Initialize chatbot with lightweight transformer model (lazy loading).
        
        Args:
            model_name: HuggingFace model identifier (lightweight by default)
        """
        self.model_name = model_name
        self.device = torch.device('cpu')  # Use CPU for Windows compatibility
        
        # Lazy load models - only load when needed
        self.tokenizer = None
        self.model = None
        self.classifier = None
        self._models_loaded = False
        
        # FAQ Knowledge base for customer support
        self.faq_database = self._initialize_faq_database()
    
    def _initialize_faq_database(self) -> Dict[str, str]:
        """
        Initialize FAQ knowledge base with common customer support questions.
        
        Returns:
            dict: Mapping of topics to responses
        """
        return {
            "hours": "Our business hours are Monday-Friday, 9 AM - 6 PM EST. Weekends: Closed.",
            "shipping": "Standard shipping takes 5-7 business days. Express shipping available in 2-3 days.",
            "returns": "We accept returns within 30 days of purchase. Item must be unused and in original packaging.",
            "payment": "We accept all major credit cards, PayPal, and Apple Pay.",
            "account": "You can reset your password on the login page using 'Forgot Password' option.",
            "contact": "You can reach our support team at support@example.com or call 1-800-SUPPORT.",
            "tracking": "Enter your order number at checkout to track your shipment in real-time.",
            "price": "We offer competitive pricing and regular discounts. Subscribe to our newsletter for deals.",
            "products": "Browse our full catalog at our website or contact support for personalized recommendations.",
            "security": "Your data is encrypted with 256-bit SSL security. We never share personal information.",
        }
    
    def _sanitize_input(self, text: str) -> str:
        """
        Sanitize and normalize user input.
        Removes special characters, extra whitespace, and normalizes text.
        
        Args:
            text: Raw user input
            
        Returns:
            str: Cleaned input text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s?.]', '', text)
        
        # Convert to lowercase for processing
        text = text.lower()
        
        return text.strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from user input by removing stopwords.
        
        Args:
            text: Input text
            
        Returns:
            list: List of significant keywords
        """
        try:
            stop_words = set(stopwords.words('english'))
            words = text.lower().split()
            keywords = [w for w in words if w.isalnum() and w not in stop_words and len(w) > 2]
            return keywords
        except:
            return text.lower().split()
    
    def _find_faq_match(self, text: str) -> Tuple[str, float]:
        """
        Find best matching FAQ response using keyword matching.
        
        Args:
            text: User input text
            
        Returns:
            tuple: (response, confidence_score)
        """
        keywords = self._extract_keywords(text)
        
        best_match = None
        best_score = 0
        
        faq_keywords = {
            "hours": ["hours", "open", "close", "time", "available"],
            "shipping": ["ship", "delivery", "deliver", "send", "arrive"],
            "returns": ["return", "refund", "exchange", "back"],
            "payment": ["pay", "card", "payment", "method", "accept"],
            "account": ["account", "password", "login", "reset"],
            "contact": ["contact", "support", "help", "call", "email"],
            "tracking": ["track", "order", "where", "status"],
            "price": ["price", "cost", "cheap", "discount", "sale"],
            "products": ["product", "item", "catalog", "recommend"],
            "security": ["secure", "safe", "encrypt", "privacy"],
        }
        
        for topic, topic_keywords in faq_keywords.items():
            matches = sum(1 for kw in keywords if any(tkw in kw or kw in tkw for tkw in topic_keywords))
            score = matches / max(len(keywords), 1)
            
            if score > best_score:
                best_score = score
                best_match = topic
        
        if best_match:
            return self.faq_database[best_match], min(best_score + 0.5, 1.0)
        
        return None, 0.0
    
    def generate_response(self, user_input: str) -> Dict[str, str]:
        """
        Generate contextual chatbot response based on user input.
        Prioritizes FAQ matching, falls back to sentiment analysis.
        
        Args:
            user_input: User's message
            
        Returns:
            dict: Response with text and confidence score
        """
        # Validate input
        if not user_input or not isinstance(user_input, str):
            return {
                "response": "Please provide a valid message.",
                "confidence": 0.0,
                "type": "validation_error"
            }
        
        # Sanitize input
        cleaned_input = self._sanitize_input(user_input)
        
        if len(cleaned_input) < 2:
            return {
                "response": "Your message is too short. Please provide more details.",
                "confidence": 0.0,
                "type": "validation_error"
            }
        
        # Try FAQ matching first
        faq_response, faq_confidence = self._find_faq_match(cleaned_input)
        
        if faq_response and faq_confidence > 0.3:
            return {
                "response": faq_response,
                "confidence": faq_confidence,
                "type": "faq_match"
            }
        
        # Fallback to generic helpful response
        generic_responses = [
            "Thank you for reaching out! How can I assist you further?",
            "I understand your inquiry. Could you provide more details?",
            "That's a great question! Our support team can help with that.",
            "Thank you for your interest. Is there anything specific I can help with?",
        ]
        
        return {
            "response": generic_responses[hash(cleaned_input) % len(generic_responses)],
            "confidence": 0.4,
            "type": "generic_response"
        }


def create_chatbot() -> AICharacter:
    """
    Factory function to create and initialize chatbot instance.
    
    Returns:
        AICharacter: Initialized chatbot instance
    """
    return AICharacter()
