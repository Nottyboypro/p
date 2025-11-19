import qrcode
import base64
import time
import random
import string
from io import BytesIO
from datetime import datetime, timedelta
from models import db, Transaction, PaymentLink, APIKey
import secrets

def generate_order_id():
    """Generate unique order ID"""
    timestamp = int(time.time())
    random_num = random.randint(1000, 9999)
    return f"BHARAT_ORD_{timestamp}_{random_num}"

def generate_merchant_id():
    """Generate merchant ID"""
    chars = string.ascii_letters + string.digits
    return 'BHARAT_' + ''.join(random.choices(chars, k=16))

def generate_qr_code(qr_data):
    """Generate QR code and return base64 encoded image"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="blue", back_color="white")
    
    buffered = BytesIO()
    qr_img.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return qr_base64

def create_payment_transaction(upi, amount, message, order_id=None, api_key_obj=None, webhook_url=None):
    """Create a new payment transaction"""
    # Generate IDs
    if not order_id:
        order_id = generate_order_id()
    
    merchant_id = generate_merchant_id()
    merchant_key = 'BHARAT_KEY_' + ''.join(random.choices(string.digits, k=12))
    
    # Create UPI payment string
    qr_data = f"upi://pay?pa={upi}&pn=BharatPay_Merchant&am={amount}&tn={message}&tr={order_id}"
    
    # Generate QR code
    qr_base64 = generate_qr_code(qr_data)
    
    # Create transaction
    transaction = Transaction(
        order_id=order_id,
        api_key_id=api_key_obj.id if api_key_obj else None,
        amount=float(amount),
        upi_id=upi,
        message=message,
        merchant_id=merchant_id,
        merchant_key=merchant_key,
        qr_data=qr_data,
        qr_code_base64=qr_base64,
        status='PENDING',
        webhook_url=webhook_url
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return transaction

def verify_payment(order_id, merchant_id, merchant_key):
    """Verify a payment transaction"""
    transaction = Transaction.query.filter_by(order_id=order_id).first()
    
    if not transaction:
        return None, "Order not found"
    
    if transaction.merchant_id != merchant_id or transaction.merchant_key != merchant_key:
        return None, "Invalid credentials"
    
    # Simulate payment verification (in production, check with payment gateway)
    # For demo: 80% success, 10% failure, 10% pending
    if transaction.status == "PENDING":
        rand = random.random()
        if rand < 0.8:  # 80% success rate
            payment_status = "TXN_SUCCESS"
        elif rand < 0.9:  # 10% failure rate
            payment_status = "TXN_FAILURE"
        else:  # 10% still pending
            payment_status = "PENDING"
        
        if payment_status == "TXN_SUCCESS":
            transaction.status = "SUCCESS"
            transaction.paid_at = datetime.utcnow()
            transaction.bharatpay_reference = f"BHARAT{int(time.time())}{random.randint(100000, 999999)}"
            transaction.bank_reference = f"BANK{random.randint(100000000, 999999999)}"
            db.session.commit()
        elif payment_status == "TXN_FAILURE":
            transaction.status = "FAILED"
            db.session.commit()
    
    return transaction, None

def create_payment_link(upi, amount, description, api_key_obj=None, max_uses=None, expires_in_hours=None):
    """Create a payment link"""
    link_id = 'link_' + secrets.token_urlsafe(16)
    
    expires_at = None
    if expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    
    payment_link = PaymentLink(
        link_id=link_id,
        api_key_id=api_key_obj.id if api_key_obj else None,
        amount=float(amount),
        upi_id=upi,
        description=description,
        max_uses=max_uses,
        expires_at=expires_at
    )
    
    db.session.add(payment_link)
    db.session.commit()
    
    return payment_link

def create_api_key(owner_name, expiry_days):
    """Create a new API key"""
    # Generate key
    api_key = APIKey.generate_key()
    key_hash = APIKey.hash_key(api_key)
    key_prefix = api_key[:12]  # First 12 chars for display
    
    # Calculate expiry
    expires_at = datetime.utcnow() + timedelta(days=int(expiry_days))
    
    # Create DB record
    api_key_obj = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        owner_name=owner_name,
        expires_at=expires_at
    )
    
    db.session.add(api_key_obj)
    db.session.commit()
    
    return api_key, api_key_obj
