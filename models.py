from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import secrets
import hashlib

db = SQLAlchemy()

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    key_prefix = db.Column(db.String(20), nullable=False)  # For display (first 8 chars)
    owner_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Usage tracking
    total_requests = db.Column(db.Integer, default=0)
    last_used_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='api_key', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_key():
        """Generate a new API key"""
        return f"bpay_{''.join(secrets.token_hex(24))}"
    
    @staticmethod
    def hash_key(key):
        """Hash an API key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def increment_usage(self):
        """Increment usage counter"""
        self.total_requests += 1
        self.last_used_at = datetime.utcnow()
        db.session.commit()
    
    def is_expired(self):
        """Check if key is expired"""
        return datetime.utcnow() > self.expires_at
    
    def __repr__(self):
        return f'<APIKey {self.key_prefix}... - {self.owner_name}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_keys.id'), nullable=True)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    upi_id = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(255), default='BharatPay Payment')
    
    # Merchant info
    merchant_id = db.Column(db.String(50), nullable=False)
    merchant_key = db.Column(db.String(50), nullable=False)
    
    # QR data
    qr_data = db.Column(db.Text, nullable=False)
    qr_code_base64 = db.Column(db.Text, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='PENDING')  # PENDING, SUCCESS, FAILED
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    
    # Webhook
    webhook_url = db.Column(db.String(500), nullable=True)
    webhook_sent = db.Column(db.Boolean, default=False)
    webhook_sent_at = db.Column(db.DateTime, nullable=True)
    
    # References
    bharatpay_reference = db.Column(db.String(100), nullable=True)
    bank_reference = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'amount': self.amount,
            'upi_id': self.upi_id,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'merchant_id': self.merchant_id,
            'bharatpay_reference': self.bharatpay_reference,
            'bank_reference': self.bank_reference
        }
    
    def __repr__(self):
        return f'<Transaction {self.order_id} - {self.status}>'

class PaymentLink(db.Model):
    __tablename__ = 'payment_links'
    
    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    api_key_id = db.Column(db.Integer, db.ForeignKey('api_keys.id'), nullable=True)
    
    # Payment details
    amount = db.Column(db.Float, nullable=False)
    upi_id = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    
    # Link settings
    is_active = db.Column(db.Boolean, default=True)
    max_uses = db.Column(db.Integer, nullable=True)  # None = unlimited
    current_uses = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_valid(self):
        """Check if payment link is still valid"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        if self.max_uses and self.current_uses >= self.max_uses:
            return False
        return True
    
    def __repr__(self):
        return f'<PaymentLink {self.link_id} - ₹{self.amount}>'

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # API_KEY, TRANSACTION, etc
    entity_id = db.Column(db.String(100), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_type}>'
