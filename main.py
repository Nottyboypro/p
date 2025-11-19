from flask import Flask, request, jsonify
import qrcode
import base64
import time
import random
import string
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# In-memory storage for transactions
transactions = {}

def generate_order_id():
    timestamp = int(time.time())
    random_num = random.randint(1000, 9999)
    return f"BHARAT_ORD_{timestamp}_{random_num}"

def generate_merchant_id():
    chars = string.ascii_letters + string.digits
    return 'BHARAT_' + ''.join(random.choices(chars, k=16))

@app.route('/bharatpay/qr', methods=['GET'])
def generate_bharatpay_qr():
    """
    BHARATPAY QR GENERATION API
    """
    try:
        # Get parameters
        upi = request.args.get('upi')
        order_id = request.args.get('order_id')
        amount = request.args.get('amount')
        message = request.args.get('message', 'BharatPay Payment')
        
        # Validate required parameters
        if not upi or not amount:
            return jsonify({
                "success": False,
                "error": "Missing required parameters: upi and amount are required"
            }), 400
        
        # Generate order ID if not provided
        if not order_id:
            order_id = generate_order_id()
        
        # Generate merchant ID
        merchant_id = generate_merchant_id()
        merchant_key = 'BHARAT_KEY_' + ''.join(random.choices(string.digits, k=12))
        
        # Create UPI payment string for BharatPay
        qr_data = f"upi://pay?pa={upi}&pn=BharatPay_Merchant&am={amount}&tn={message}&tr={order_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="blue", back_color="white")
        
        # Convert to base64
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Store transaction details
        transactions[order_id] = {
            "order_id": order_id,
            "amount": amount,
            "merchant_id": merchant_id,
            "merchant_key": merchant_key,
            "qr_data": qr_data,
            "timestamp": int(time.time()),
            "status": "PENDING",
            "upi": upi,
            "message": message,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Success response - BHARATPAY STYLE
        response = {
            "success": True,
            "api_provider": "BharatPay",
            "order_id": order_id,
            "qr_code": qr_base64,
            "qr_data": qr_data,
            "amount": amount,
            "purpose": message,
            "merchant_upi": upi,
            "merchant_name": "BharatPay Merchant",
            "timestamp": int(time.time()),
            "merchant_id": merchant_id,
            "merchant_key": merchant_key,
            "verify_url": "Use /bharatpay/verify with order_id, merchant_id and merchant_key",
            "instructions": "Scan this QR with any UPI app to pay via BharatPay"
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"BharatPay API Error: {str(e)}"
        }), 500

@app.route('/bharatpay/verify', methods=['GET'])
def verify_bharatpay_payment():
    """
    BHARATPAY PAYMENT VERIFICATION API
    """
    try:
        # Get parameters
        order_id = request.args.get('order_id')
        merchant_id = request.args.get('merchant_id')
        merchant_key = request.args.get('merchant_key')
        
        # Validate required parameters
        if not order_id or not merchant_id or not merchant_key:
            return jsonify({
                "success": False,
                "error": "Missing required parameters: order_id, merchant_id and merchant_key are required"
            }), 400
        
        # Check if transaction exists
        if order_id not in transactions:
            return jsonify({
                "success": False,
                "status": "TXN_FAILURE",
                "transaction_id": order_id,
                "merchant_id": merchant_id,
                "error": "BharatPay Payment verification failed ❌",
                "message": "Invalid Order Id."
            }), 404
        
        transaction = transactions[order_id]
        
        # Check if merchant credentials match
        if transaction['merchant_id'] != merchant_id or transaction['merchant_key'] != merchant_key:
            return jsonify({
                "success": False,
                "status": "TXN_FAILURE",
                "transaction_id": order_id,
                "merchant_id": merchant_id,
                "error": "BharatPay Payment verification failed ❌",
                "message": "Invalid Merchant Credentials."
            }), 400
        
        # Simulate payment verification - BharatPay Style
        # In real scenario, integrate with BharatPay official API
        payment_status = random.choice(["TXN_SUCCESS", "TXN_FAILURE", "PENDING"])
        
        if payment_status == "TXN_SUCCESS":
            # Update transaction status
            transactions[order_id]['status'] = "SUCCESS"
            transactions[order_id]['paid_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.0")
            
            response = {
                "success": True,
                "api_provider": "BharatPay",
                "status": "TXN_SUCCESS",
                "transaction_id": order_id,
                "amount": transaction['amount'],
                "merchant_id": merchant_id,
                "message": "BharatPay Payment verified successfully ✅",
                "bharatpay_reference": f"BHARAT{int(time.time())}{random.randint(100000, 999999)}",
                "bank_reference": f"BANK{random.randint(100000000, 999999999)}",
                "timestamp": transactions[order_id]['paid_at'],
                "payment_mode": "UPI",
                "gateway": "BharatPay"
            }
        elif payment_status == "TXN_FAILURE":
            response = {
                "success": False,
                "api_provider": "BharatPay",
                "status": "TXN_FAILURE",
                "transaction_id": order_id,
                "merchant_id": merchant_id,
                "error": "BharatPay Payment verification failed ❌",
                "message": "Payment not completed or failed."
            }
        else:
            response = {
                "success": False,
                "api_provider": "BharatPay",
                "status": "PENDING",
                "transaction_id": order_id,
                "merchant_id": merchant_id,
                "message": "Payment is still pending. Please try again later."
            }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"BharatPay Verification Error: {str(e)}"
        }), 500

@app.route('/bharatpay/transactions', methods=['GET'])
def get_bharatpay_transactions():
    """
    Get all BharatPay transactions (for admin/testing)
    """
    return jsonify({
        "success": True,
        "api_provider": "BharatPay",
        "total_transactions": len(transactions),
        "transactions": transactions
    })

@app.route('/bharatpay/simulate_payment', methods=['POST'])
def simulate_bharatpay_payment():
    """
    Simulate BharatPay payment completion (for testing)
    """
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        status = data.get('status', 'SUCCESS')
        
        if order_id in transactions:
            transactions[order_id]['status'] = status
            transactions[order_id]['paid_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.0")
            
            return jsonify({
                "success": True,
                "api_provider": "BharatPay",
                "message": f"BharatPay Payment simulated for order {order_id}",
                "status": status
            })
        else:
            return jsonify({
                "success": False,
                "error": "Order ID not found in BharatPay records"
            }), 404
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"BharatPay Simulation Error: {str(e)}"
        }), 500

@app.route('/bharatpay/status', methods=['GET'])
def bharatpay_status():
    """
    BharatPay API Status Check
    """
    return jsonify({
        "success": True,
        "api_provider": "BharatPay",
        "status": "🟢 LIVE",
        "message": "BharatPay QR Payment API is running successfully",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "endpoints": {
            "qr_generate": "GET /bharatpay/qr?upi=your@upi&amount=100",
            "verify": "GET /bharatpay/verify?order_id=ORDER_ID&merchant_id=M_ID&merchant_key=M_KEY",
            "transactions": "GET /bharatpay/transactions",
            "simulate": "POST /bharatpay/simulate_payment"
        }
    })

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>🚀 BharatPay QR Payment API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f0f8ff; }
                .container { max-width: 800px; margin: 0 auto; }
                .header { background: #0066cc; color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .endpoint { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
                code { background: #f5f5f5; padding: 3px 6px; border-radius: 3px; font-family: monospace; }
                .success { color: green; font-weight: bold; }
                .endpoint h3 { color: #0066cc; margin-top: 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 BharatPay QR Payment API</h1>
                    <p>Powered by Python Flask | Made for BharatPay UPI Payments</p>
                </div>
                
                <div class="endpoint">
                    <h3>🔵 1. BharatPay QR Generate API</h3>
                    <p><code>GET /bharatpay/qr?upi=merchant@bharatpay&amount=100&order_id=BHARAT_123</code></p>
                    <p><strong>Parameters:</strong> upi, amount, order_id (optional), message (optional)</p>
                    <p class="success">Returns: Base64 QR Code + Payment Details</p>
                </div>
                
                <div class="endpoint">
                    <h3>🟠 2. BharatPay Payment Verify API</h3>
                    <p><code>GET /bharatpay/verify?order_id=BHARAT_123&merchant_id=ID&merchant_key=KEY</code></p>
                    <p><strong>Parameters:</strong> order_id, merchant_id, merchant_key</p>
                    <p class="success">Returns: Payment Status + Transaction Details</p>
                </div>
                
                <div class="endpoint">
                    <h3>📊 3. Check API Status</h3>
                    <p><code>GET /bharatpay/status</code></p>
                    <p>Check if BharatPay API is running</p>
                </div>
                
                <div class="endpoint">
                    <h3>🛠 4. Testing Endpoints</h3>
                    <p><code>GET /bharatpay/transactions</code> - View all transactions</p>
                    <p><code>POST /bharatpay/simulate_payment</code> - Simulate payment (for testing)</p>
                </div>
                
                <div class="endpoint">
                    <h3>💡 Example Usage (Python):</h3>
                    <pre><code>
import requests

# Generate QR
response = requests.get("http://localhost:5000/bharatpay/qr?upi=test@bharatpay&amount=100")
data = response.json()
print(data['qr_code'])  # Base64 QR Image

# Verify Payment  
verify = requests.get(f"http://localhost:5000/bharatpay/verify?order_id={data['order_id']}&merchant_id={data['merchant_id']}&merchant_key={data['merchant_key']}")
print(verify.json())
                    </code></pre>
                </div>
            </div>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
