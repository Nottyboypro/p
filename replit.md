# BharatPay QR Payment API

## Overview
BharatPay is a Flask-based REST API for generating UPI QR codes and verifying payments. It provides a complete payment flow simulation for BharatPay-style transactions.

**Current State:** ✅ Running and fully functional
**Language:** Python 3.11
**Framework:** Flask with Gunicorn
**Port:** 5000

## Project Architecture

### Technology Stack
- **Backend:** Flask 3.0.3
- **WSGI Server:** Gunicorn 23.0.0
- **QR Generation:** qrcode 7.4.2 + Pillow 10.4.0
- **Storage:** In-memory (dictionary-based)

### Project Structure
```
.
├── main.py              # Main Flask application
├── requirements.txt     # Python dependencies
├── runtime.txt          # Python version specification
├── Procfile            # Deployment configuration
├── .gitignore          # Git ignore rules
└── replit.md           # This documentation
```

### API Endpoints

1. **Home** - `GET /`
   - Returns HTML documentation page

2. **Status Check** - `GET /bharatpay/status`
   - Health check endpoint
   - Returns API status and available endpoints

3. **QR Generation** - `GET /bharatpay/qr`
   - Parameters: `upi` (required), `amount` (required), `order_id` (optional), `message` (optional)
   - Returns: Base64 QR code, order details, merchant credentials

4. **Payment Verification** - `GET /bharatpay/verify`
   - Parameters: `order_id`, `merchant_id`, `merchant_key`
   - Returns: Payment status (TXN_SUCCESS, TXN_FAILURE, or PENDING)

5. **View Transactions** - `GET /bharatpay/transactions`
   - Returns all stored transactions (admin/testing)

6. **Simulate Payment** - `POST /bharatpay/simulate_payment`
   - Body: `{"order_id": "...", "status": "SUCCESS"}`
   - Manually set payment status for testing

## Recent Changes
- **2025-11-19:** Initial setup in Replit environment
  - Installed Python 3.11 and dependencies
  - Configured Gunicorn workflow on port 5000
  - Added .gitignore for Python projects
  - API is live and running

## Deployment

The API is configured for deployment with:
- Gunicorn as production server
- Port binding to 0.0.0.0:5000
- Worker process with socket reuse

## Notes
- Uses in-memory storage (data clears on restart)
- Payment verification is simulated (random success/failure)
- For production use, integrate with real BharatPay API and use persistent database
