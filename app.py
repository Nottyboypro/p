from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from models import db, Admin, APIKey, Transaction, PaymentLink, AuditLog
from auth import hash_password, verify_password, admin_required, api_key_required, log_audit
from services import create_payment_transaction, verify_payment, create_payment_link, create_api_key
import os

# Initialize Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
app.config.from_object(Config)

# Initialize extensions
CORS(app)
db.init_app(app)
jwt = JWTManager(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=app.config['RATELIMIT_STORAGE_URL']
)

# ========== ADMIN AUTHENTICATION ==========

@app.route('/api/admin/login', methods=['POST'])
@limiter.limit("5 per minute")
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password required'
            }), 400
        
        admin = Admin.query.filter_by(username=username).first()
        
        if not admin or not verify_password(password, admin.password_hash):
            log_audit('ADMIN_LOGIN_FAILED', 'ADMIN', username, 'Invalid credentials')
            return jsonify({
                'success': False,
                'error': 'Invalid credentials'
            }), 401
        
        access_token = create_access_token(identity=username)
        log_audit('ADMIN_LOGIN_SUCCESS', 'ADMIN', str(admin.id), f'Admin {username} logged in')
        
        return jsonify({
            'success': True,
            'access_token': access_token,
            'username': username
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/verify', methods=['GET'])
@admin_required
def verify_admin():
    """Verify admin token"""
    return jsonify({
        'success': True,
        'username': get_jwt_identity()
    })

# ========== API KEY MANAGEMENT (ADMIN ONLY) ==========

@app.route('/api/admin/api-keys', methods=['GET'])
@admin_required
def get_api_keys():
    """Get all API keys"""
    try:
        keys = APIKey.query.order_by(APIKey.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'api_keys': [{
                'id': k.id,
                'key_prefix': k.key_prefix,
                'owner_name': k.owner_name,
                'created_at': k.created_at.isoformat(),
                'expires_at': k.expires_at.isoformat(),
                'is_active': k.is_active,
                'is_expired': k.is_expired(),
                'total_requests': k.total_requests,
                'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None
            } for k in keys]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/api-keys', methods=['POST'])
@admin_required
def create_new_api_key():
    """Create a new API key"""
    try:
        data = request.get_json()
        owner_name = data.get('owner_name')
        expiry_days = data.get('expiry_days')
        
        if not owner_name or not expiry_days:
            return jsonify({
                'success': False,
                'error': 'owner_name and expiry_days required'
            }), 400
        
        api_key, api_key_obj = create_api_key(owner_name, expiry_days)
        
        log_audit('API_KEY_CREATED', 'API_KEY', str(api_key_obj.id), f'Created for {owner_name}')
        
        return jsonify({
            'success': True,
            'message': 'API key created successfully',
            'api_key': api_key,  # ONLY shown once!
            'key_prefix': api_key_obj.key_prefix,
            'owner_name': api_key_obj.owner_name,
            'expires_at': api_key_obj.expires_at.isoformat(),
            'warning': 'Save this key securely. It will not be shown again!'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/api-keys/<int:key_id>', methods=['DELETE'])
@admin_required
def delete_api_key(key_id):
    """Delete an API key"""
    try:
        api_key_obj = APIKey.query.get(key_id)
        if not api_key_obj:
            return jsonify({'success': False, 'error': 'API key not found'}), 404
        
        log_audit('API_KEY_DELETED', 'API_KEY', str(key_id), f'Deleted key for {api_key_obj.owner_name}')
        
        db.session.delete(api_key_obj)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'API key deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/api-keys/<int:key_id>/toggle', methods=['POST'])
@admin_required
def toggle_api_key(key_id):
    """Activate/deactivate an API key"""
    try:
        api_key_obj = APIKey.query.get(key_id)
        if not api_key_obj:
            return jsonify({'success': False, 'error': 'API key not found'}), 404
        
        api_key_obj.is_active = not api_key_obj.is_active
        db.session.commit()
        
        log_audit(
            'API_KEY_TOGGLED', 
            'API_KEY', 
            str(key_id), 
            f'Set to {"active" if api_key_obj.is_active else "inactive"}'
        )
        
        return jsonify({
            'success': True,
            'message': f'API key {"activated" if api_key_obj.is_active else "deactivated"}',
            'is_active': api_key_obj.is_active
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== TRANSACTIONS (ADMIN ONLY) ==========

@app.route('/api/admin/transactions', methods=['GET'])
@admin_required
def get_all_transactions():
    """Get all transactions"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        transactions = Transaction.query.order_by(Transaction.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'transactions': [t.to_dict() for t in transactions.items],
            'total': transactions.total,
            'pages': transactions.pages,
            'current_page': page
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_stats():
    """Get dashboard statistics"""
    try:
        total_transactions = Transaction.query.count()
        total_api_keys = APIKey.query.count()
        active_api_keys = APIKey.query.filter_by(is_active=True).count()
        
        successful_payments = Transaction.query.filter_by(status='SUCCESS').count()
        total_amount = db.session.query(db.func.sum(Transaction.amount)).filter_by(status='SUCCESS').scalar() or 0
        
        pending_payments = Transaction.query.filter_by(status='PENDING').count()
        failed_payments = Transaction.query.filter_by(status='FAILED').count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_transactions': total_transactions,
                'total_api_keys': total_api_keys,
                'active_api_keys': active_api_keys,
                'successful_payments': successful_payments,
                'pending_payments': pending_payments,
                'failed_payments': failed_payments,
                'total_amount': float(total_amount)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== PUBLIC API ENDPOINTS (REQUIRE API KEY) ==========

@app.route('/api/v1/qr/generate', methods=['POST'])
@api_key_required
@limiter.limit("100 per hour")
def generate_qr():
    """Generate QR code for payment"""
    try:
        data = request.get_json()
        upi = data.get('upi')
        amount = data.get('amount')
        message = data.get('message', 'BharatPay Payment')
        order_id = data.get('order_id')
        webhook_url = data.get('webhook_url')
        
        if not upi or not amount:
            return jsonify({
                'success': False,
                'error': 'upi and amount are required'
            }), 400
        
        transaction = create_payment_transaction(
            upi, amount, message, order_id, 
            api_key_obj=request.api_key_obj,
            webhook_url=webhook_url
        )
        
        log_audit('TRANSACTION_CREATED', 'TRANSACTION', transaction.order_id, f'Amount: {amount}')
        
        return jsonify({
            'success': True,
            'order_id': transaction.order_id,
            'merchant_id': transaction.merchant_id,
            'merchant_key': transaction.merchant_key,
            'qr_code': transaction.qr_code_base64,
            'qr_data': transaction.qr_data,
            'amount': transaction.amount,
            'upi_id': transaction.upi_id,
            'message': transaction.message,
            'status': transaction.status,
            'created_at': transaction.created_at.isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/v1/payment/verify', methods=['POST'])
@api_key_required
@limiter.limit("200 per hour")
def verify_payment_api():
    """Verify payment status"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        merchant_id = data.get('merchant_id')
        merchant_key = data.get('merchant_key')
        
        if not order_id or not merchant_id or not merchant_key:
            return jsonify({
                'success': False,
                'error': 'order_id, merchant_id, and merchant_key are required'
            }), 400
        
        transaction, error = verify_payment(order_id, merchant_id, merchant_key)
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 404 if error == "Order not found" else 400
        
        log_audit('PAYMENT_VERIFIED', 'TRANSACTION', order_id, f'Status: {transaction.status}')
        
        response = {
            'success': True,
            'order_id': transaction.order_id,
            'status': transaction.status,
            'amount': transaction.amount,
            'created_at': transaction.created_at.isoformat()
        }
        
        if transaction.status == 'SUCCESS':
            response.update({
                'paid_at': transaction.paid_at.isoformat(),
                'bharatpay_reference': transaction.bharatpay_reference,
                'bank_reference': transaction.bank_reference
            })
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== PAYMENT LINKS ==========

@app.route('/api/v1/payment-link/create', methods=['POST'])
@api_key_required
def create_new_payment_link():
    """Create a payment link"""
    try:
        data = request.get_json()
        upi = data.get('upi')
        amount = data.get('amount')
        description = data.get('description', 'Payment')
        max_uses = data.get('max_uses')
        expires_in_hours = data.get('expires_in_hours')
        
        if not upi or not amount:
            return jsonify({
                'success': False,
                'error': 'upi and amount are required'
            }), 400
        
        payment_link = create_payment_link(
            upi, amount, description,
            api_key_obj=request.api_key_obj,
            max_uses=max_uses,
            expires_in_hours=expires_in_hours
        )
        
        # Get domain for full URL
        domain = request.host_url.rstrip('/')
        
        return jsonify({
            'success': True,
            'link_id': payment_link.link_id,
            'payment_url': f'{domain}/pay/{payment_link.link_id}',
            'amount': payment_link.amount,
            'description': payment_link.description,
            'expires_at': payment_link.expires_at.isoformat() if payment_link.expires_at else None,
            'max_uses': payment_link.max_uses
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== PUBLIC PAGES (NO AUTH REQUIRED) ==========

@app.route('/pay/<link_id>', methods=['GET'])
def payment_link_page(link_id):
    """Public payment link page"""
    payment_link = PaymentLink.query.filter_by(link_id=link_id).first()
    
    if not payment_link:
        return "Payment link not found", 404
    
    if not payment_link.is_valid():
        return "Payment link expired or invalid", 400
    
    # Serve payment page (we'll create this HTML later)
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BharatPay - Payment</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .container {{
                background: white;
                border-radius: 16px;
                padding: 40px;
                max-width: 400px;
                width: 100%;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }}
            h1 {{
                color: #333;
                margin-top: 0;
                text-align: center;
            }}
            .amount {{
                font-size: 48px;
                font-weight: bold;
                color: #667eea;
                text-align: center;
                margin: 20px 0;
            }}
            .description {{
                text-align: center;
                color: #666;
                margin-bottom: 30px;
            }}
            .qr-container {{
                text-align: center;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
                margin: 20px 0;
            }}
            .qr-img {{
                max-width: 250px;
                width: 100%;
            }}
            .instructions {{
                background: #e3f2fd;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                font-size: 14px;
                color: #1976d2;
            }}
            button {{
                width: 100%;
                padding: 15px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 15px;
            }}
            button:hover {{
                background: #5568d3;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💳 BharatPay</h1>
            <div class="amount">₹{payment_link.amount}</div>
            <div class="description">{payment_link.description}</div>
            
            <div id="qr-section" style="display:none;">
                <div class="qr-container">
                    <img class="qr-img" id="qr-image" />
                </div>
                <div class="instructions">
                    📱 Scan this QR code with any UPI app (Google Pay, PhonePe, Paytm, etc.) to complete the payment
                </div>
            </div>
            
            <button onclick="generateQR()">Generate Payment QR</button>
            <div id="order-info" style="display:none; margin-top:20px; font-size:12px; color:#666; text-align:center;"></div>
        </div>
        
        <script>
            let orderData = null;
            
            async function generateQR() {{
                try {{
                    // For demo, we'll create QR directly without API key
                    // In production, this would go through your backend
                    const response = await fetch('/api/public/pay/{link_id}', {{
                        method: 'POST'
                    }});
                    
                    const data = await response.json();
                    
                    if (data.success) {{
                        orderData = data;
                        document.getElementById('qr-image').src = 'data:image/png;base64,' + data.qr_code;
                        document.getElementById('qr-section').style.display = 'block';
                        document.getElementById('order-info').innerHTML = 'Order ID: ' + data.order_id;
                        document.getElementById('order-info').style.display = 'block';
                    }}
                }} catch (error) {{
                    alert('Error generating QR code');
                }}
            }}
        </script>
    </body>
    </html>
    """

@app.route('/api/public/pay/<link_id>', methods=['POST'])
def generate_qr_for_link(link_id):
    """Generate QR for payment link (public, no API key required)"""
    try:
        payment_link = PaymentLink.query.filter_by(link_id=link_id).first()
        
        if not payment_link or not payment_link.is_valid():
            return jsonify({
                'success': False,
                'error': 'Payment link invalid or expired'
            }), 400
        
        # Create transaction
        transaction = create_payment_transaction(
            payment_link.upi_id,
            payment_link.amount,
            payment_link.description,
            api_key_obj=None
        )
        
        # Increment usage
        payment_link.current_uses += 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'order_id': transaction.order_id,
            'merchant_id': transaction.merchant_id,
            'merchant_key': transaction.merchant_key,
            'qr_code': transaction.qr_code_base64,
            'amount': transaction.amount
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========== API DOCUMENTATION ==========

@app.route('/api/docs', methods=['GET'])
def api_docs():
    """API documentation"""
    return jsonify({
        'name': 'BharatPay API',
        'version': '2.0',
        'description': 'Production-ready UPI payment gateway API',
        'endpoints': {
            'admin': {
                'login': 'POST /api/admin/login',
                'verify': 'GET /api/admin/verify',
                'api_keys': 'GET /api/admin/api-keys',
                'create_key': 'POST /api/admin/api-keys',
                'delete_key': 'DELETE /api/admin/api-keys/:id',
                'transactions': 'GET /api/admin/transactions',
                'stats': 'GET /api/admin/stats'
            },
            'developer_api': {
                'generate_qr': 'POST /api/v1/qr/generate (requires API key)',
                'verify_payment': 'POST /api/v1/payment/verify (requires API key)',
                'create_payment_link': 'POST /api/v1/payment-link/create (requires API key)'
            },
            'public': {
                'payment_link': 'GET /pay/:link_id'
            }
        }
    })

# ========== SERVE STATIC PAGES ==========

@app.route('/')
def home():
    """Serve homepage"""
    return send_from_directory('static', 'home.html')

@app.route('/admin')
def serve_admin():
    """Serve admin panel"""
    return send_from_directory('static', 'admin.html')

@app.route('/playground')
def serve_playground():
    """Serve developer playground"""
    return send_from_directory('static', 'playground.html')

# ========== DATABASE INITIALIZATION ==========

def init_db():
    """Initialize database and create default admin"""
    with app.app_context():
        db.create_all()
        
        # Create default admin if doesn't exist
        admin = Admin.query.filter_by(username=app.config['ADMIN_USERNAME']).first()
        if not admin:
            admin = Admin(
                username=app.config['ADMIN_USERNAME'],
                password_hash=hash_password(app.config['ADMIN_PASSWORD'])
            )
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Default admin created: {app.config['ADMIN_USERNAME']}")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
