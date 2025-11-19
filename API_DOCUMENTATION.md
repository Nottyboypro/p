# BharatPay API Documentation v2.0

## 🚀 Overview

BharatPay is a professional-grade UPI payment gateway API that allows developers to integrate UPI QR code payments into their applications. The system includes:

- **Admin Panel**: Secure dashboard for managing API keys, viewing transactions, and analytics
- **Developer API**: RESTful API with authentication for payment operations
- **User Interface**: Public payment pages for end-users

## 🔐 Authentication

### Admin Authentication
Admin endpoints use **JWT Bearer tokens**. Login to get your access token.

### Developer Authentication
API endpoints require an **API Key** in the header:
```
X-API-Key: your_api_key_here
```

Or as a query parameter:
```
?api_key=your_api_key_here
```

## 📡 Admin Panel Endpoints

### 1. Admin Login
```http
POST /api/admin/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

**Response:**
```json
{
    "success": true,
    "access_token": "eyJ0eXAiOiJKV1QiLCJ...",
    "username": "admin"
}
```

### 2. Verify Admin Token
```http
GET /api/admin/verify
Authorization: Bearer <token>
```

### 3. Get Dashboard Statistics
```http
GET /api/admin/stats
Authorization: Bearer <token>
```

**Response:**
```json
{
    "success": true,
    "stats": {
        "total_transactions": 150,
        "total_api_keys": 5,
        "active_api_keys": 4,
        "successful_payments": 120,
        "pending_payments": 25,
        "failed_payments": 5,
        "total_amount": 45000.00
    }
}
```

### 4. Get All API Keys
```http
GET /api/admin/api-keys
Authorization: Bearer <token>
```

### 5. Create New API Key
```http
POST /api/admin/api-keys
Authorization: Bearer <token>
Content-Type: application/json

{
    "owner_name": "John's E-commerce App",
    "expiry_days": 365
}
```

**Response:**
```json
{
    "success": true,
    "message": "API key created successfully",
    "api_key": "bpay_1a2b3c4d5e6f7g8h9i0j...",
    "key_prefix": "bpay_1a2b3c4",
    "owner_name": "John's E-commerce App",
    "expires_at": "2026-11-19T10:30:00",
    "warning": "Save this key securely. It will not be shown again!"
}
```

### 6. Delete API Key
```http
DELETE /api/admin/api-keys/{key_id}
Authorization: Bearer <token>
```

### 7. Toggle API Key Status
```http
POST /api/admin/api-keys/{key_id}/toggle
Authorization: Bearer <token>
```

### 8. Get All Transactions
```http
GET /api/admin/transactions?page=1&per_page=50
Authorization: Bearer <token>
```

## 💳 Developer API Endpoints

All developer endpoints require a valid API key.

### 1. Generate Payment QR Code
```http
POST /api/v1/qr/generate
X-API-Key: your_api_key_here
Content-Type: application/json

{
    "upi": "merchant@upi",
    "amount": 500,
    "message": "Order #12345",
    "order_id": "ORD_12345",  // Optional
    "webhook_url": "https://yoursite.com/webhook"  // Optional
}
```

**Response:**
```json
{
    "success": true,
    "order_id": "BHARAT_ORD_1700485678_1234",
    "merchant_id": "BHARAT_abc123...",
    "merchant_key": "BHARAT_KEY_123456789012",
    "qr_code": "iVBORw0KGgoAAAANS...",  // Base64 encoded QR image
    "qr_data": "upi://pay?pa=merchant@upi&pn=BharatPay_Merchant&am=500&tn=Order #12345&tr=BHARAT_ORD_...",
    "amount": 500,
    "upi_id": "merchant@upi",
    "message": "Order #12345",
    "status": "PENDING",
    "created_at": "2025-11-19T16:30:00"
}
```

### 2. Verify Payment Status
```http
POST /api/v1/payment/verify
X-API-Key: your_api_key_here
Content-Type: application/json

{
    "order_id": "BHARAT_ORD_1700485678_1234",
    "merchant_id": "BHARAT_abc123...",
    "merchant_key": "BHARAT_KEY_123456789012"
}
```

**Response (Success):**
```json
{
    "success": true,
    "order_id": "BHARAT_ORD_1700485678_1234",
    "status": "SUCCESS",
    "amount": 500,
    "created_at": "2025-11-19T16:30:00",
    "paid_at": "2025-11-19T16:32:45",
    "bharatpay_reference": "BHARAT1700485765123456",
    "bank_reference": "BANK987654321"
}
```

**Response (Pending):**
```json
{
    "success": true,
    "order_id": "BHARAT_ORD_1700485678_1234",
    "status": "PENDING",
    "amount": 500,
    "created_at": "2025-11-19T16:30:00"
}
```

### 3. Create Payment Link
```http
POST /api/v1/payment-link/create
X-API-Key: your_api_key_here
Content-Type: application/json

{
    "upi": "merchant@upi",
    "amount": 299,
    "description": "Premium Subscription",
    "max_uses": 100,  // Optional
    "expires_in_hours": 168  // Optional (7 days)
}
```

**Response:**
```json
{
    "success": true,
    "link_id": "link_abc123def456...",
    "payment_url": "https://your-domain.com/pay/link_abc123def456...",
    "amount": 299,
    "description": "Premium Subscription",
    "expires_at": "2025-11-26T16:30:00",
    "max_uses": 100
}
```

## 🌐 Public Payment Pages

### Payment Link Page
```http
GET /pay/{link_id}
```

This displays a user-friendly payment page where customers can:
1. View payment amount and description
2. Generate UPI QR code
3. Scan and pay using any UPI app
4. Track payment status

## 📊 Rate Limits

- **Admin Login**: 5 requests per minute
- **QR Generation**: 100 requests per hour (per API key)
- **Payment Verification**: 200 requests per hour (per API key)

## 🔍 Error Responses

All errors follow this format:
```json
{
    "success": false,
    "error": "Error message description"
}
```

Common HTTP Status Codes:
- `200`: Success
- `400`: Bad Request (missing/invalid parameters)
- `401`: Unauthorized (invalid/missing API key or token)
- `404`: Not Found
- `429`: Too Many Requests (rate limit exceeded)
- `500`: Internal Server Error

## 💡 Example Integration (Python)

```python
import requests
import base64
from PIL import Image
from io import BytesIO

# Your API key
API_KEY = "bpay_your_api_key_here"
BASE_URL = "https://your-bharatpay-domain.com"

# 1. Generate Payment QR
def create_payment(upi, amount, message):
    response = requests.post(
        f"{BASE_URL}/api/v1/qr/generate",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "upi": upi,
            "amount": amount,
            "message": message
        }
    )
    
    data = response.json()
    
    if data['success']:
        # Decode and display QR code
        qr_bytes = base64.b64decode(data['qr_code'])
        qr_image = Image.open(BytesIO(qr_bytes))
        qr_image.show()
        
        return data
    else:
        print(f"Error: {data['error']}")
        return None

# 2. Verify Payment
def verify_payment(order_id, merchant_id, merchant_key):
    response = requests.post(
        f"{BASE_URL}/api/v1/payment/verify",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "order_id": order_id,
            "merchant_id": merchant_id,
            "merchant_key": merchant_key
        }
    )
    
    data = response.json()
    return data

# Example usage
payment = create_payment("merchant@upi", 500, "Order #12345")
if payment:
    print(f"Payment created: {payment['order_id']}")
    print("Show QR code to customer...")
    
    # Poll for payment status
    import time
    for _ in range(30):  # Check for 5 minutes
        time.sleep(10)
        status = verify_payment(
            payment['order_id'],
            payment['merchant_id'],
            payment['merchant_key']
        )
        
        if status['status'] == 'SUCCESS':
            print(f"✅ Payment successful!")
            print(f"Reference: {status['bharatpay_reference']}")
            break
        elif status['status'] == 'FAILED':
            print("❌ Payment failed")
            break
        else:
            print("⏳ Payment pending...")
```

## 🔒 Security Best Practices

1. **Never expose API keys** in client-side code
2. **Store API keys** in environment variables
3. **Use HTTPS** in production
4. **Rotate API keys** periodically
5. **Monitor API usage** through admin dashboard
6. **Implement webhook signatures** for payment callbacks
7. **Set appropriate expiry** for API keys

## 🎯 Webhooks (Coming Soon)

Configure webhook URLs when creating payments to receive real-time payment status updates:

```json
{
    "event": "payment.success",
    "order_id": "BHARAT_ORD_...",
    "status": "SUCCESS",
    "amount": 500,
    "bharatpay_reference": "BHARAT1700485765123456",
    "timestamp": "2025-11-19T16:32:45"
}
```

## 📞 Support

For API issues or questions:
- Check the admin dashboard for API usage stats
- Review audit logs for debugging
- Monitor transaction status in real-time

---

**BharatPay API v2.0** - Production-Ready UPI Payment Gateway
