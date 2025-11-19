import bcrypt
from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import APIKey, db, AuditLog
from datetime import datetime

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def admin_required(fn):
    """Decorator to require admin authentication via JWT"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Admin authentication required'
            }), 401
    return wrapper

def api_key_required(fn):
    """Decorator to require valid API key"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Get API key from header
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            log_audit('API_KEY_MISSING', 'API_KEY', None, 'API key not provided')
            return jsonify({
                'success': False,
                'error': 'API key required. Provide X-API-Key header or api_key parameter'
            }), 401
        
        # Demo mode - allow "demo-mode" as API key for testing
        if api_key == 'demo-mode':
            request.api_key_obj = None  # Demo mode has no associated key
            log_audit('DEMO_MODE_ACCESS', 'API_KEY', 'demo', 'Demo mode API access')
            return fn(*args, **kwargs)
        
        # Hash and lookup
        key_hash = APIKey.hash_key(api_key)
        api_key_obj = APIKey.query.filter_by(key_hash=key_hash).first()
        
        if not api_key_obj:
            log_audit('API_KEY_INVALID', 'API_KEY', None, 'Invalid API key provided')
            return jsonify({
                'success': False,
                'error': 'Invalid API key'
            }), 401
        
        if not api_key_obj.is_active:
            log_audit('API_KEY_INACTIVE', 'API_KEY', str(api_key_obj.id), 'Inactive API key used')
            return jsonify({
                'success': False,
                'error': 'API key is inactive'
            }), 401
        
        if api_key_obj.is_expired():
            log_audit('API_KEY_EXPIRED', 'API_KEY', str(api_key_obj.id), 'Expired API key used')
            return jsonify({
                'success': False,
                'error': 'API key has expired'
            }), 401
        
        # Increment usage
        api_key_obj.increment_usage()
        
        # Add to request context
        request.api_key_obj = api_key_obj
        
        return fn(*args, **kwargs)
    return wrapper

def log_audit(action, entity_type, entity_id=None, details=None):
    """Log an audit event"""
    try:
        audit = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(audit)
        db.session.commit()
    except:
        pass  # Don't fail if audit logging fails
