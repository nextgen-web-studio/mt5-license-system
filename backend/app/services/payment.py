import razorpay
import os
from dotenv import load_dotenv

import requests

# Patch requests to bypass local SSL certificate issues for Razorpay
old_request = requests.Session.request
def new_request(*args, **kwargs):
    kwargs['verify'] = False
    return old_request(*args, **kwargs)
requests.Session.request = new_request

load_dotenv()

RAZORPAY_KEY = os.getenv("RAZORPAY_API_KEY", "rzp_test_TMkPB4Kf0yKrRE")
RAZORPAY_SECRET = os.getenv("RAZORPAY_API_SECRET", "rA0JKeTg2CLs8aCe2AP8rzNv")

client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

def create_razorpay_order(amount: float, currency: str = "INR", receipt: str = None) -> dict:
    """
    Creates an order in Razorpay.
    """
    data = {
        "amount": int(amount * 100), # Razorpay expects amount in paise
        "currency": currency,
        "receipt": receipt
    }
    return client.order.create(data=data)

def create_payment_link(amount: float, reference_id: str, description: str = "Infinity Trader Order") -> dict:
    """
    Creates a Razorpay Payment Link.
    """
    data = {
        "amount": int(amount * 100),
        "currency": "INR",
        "accept_partial": False,
        "description": description,
        "reference_id": reference_id,
        "notify": {
            "sms": False,
            "email": False
        },
        "reminder_enable": False,
        "callback_method": "get"
    }
    return client.payment_link.create(data)

def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> bool:
    """
    Verifies the signature sent by Razorpay.
    """
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    try:
        return client.utility.verify_payment_signature(params_dict)
    except Exception as e:
        return False

def verify_webhook_signature(body: str, signature: str, secret: str) -> bool:
    """
    Verifies the webhook signature.
    """
    try:
        return client.utility.verify_webhook_signature(body, signature, secret)
    except Exception as e:
        return False
