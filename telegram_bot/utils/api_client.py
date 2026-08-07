import httpx
import logging

import os

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

async def register_user(telegram_id, name, username, phone=None):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/users/",
                json={
                    "telegram_id": str(telegram_id),
                    "name": name,
                    "username": username or "",
                    "phone": phone
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            return None

async def get_products(product_type=None):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/products/")
            response.raise_for_status()
            products = response.json()
            if product_type:
                products = [p for p in products if p['type'] == product_type]
            return products
        except Exception as e:
            logging.error(f"Error fetching products: {e}")
            return []

async def create_order(user_id, product_id, order_type):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/orders/",
                json={
                    "user_id": user_id,
                    "product_id": product_id,
                    "order_type": order_type
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error creating order: {e}")
            return None

async def create_payment(order_id, amount):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/payments/create-payment-link",
                json={
                    "order_id": order_id,
                    "amount": amount
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error creating payment: {e}")
            return None
