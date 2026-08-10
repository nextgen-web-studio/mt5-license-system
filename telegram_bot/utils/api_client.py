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

async def get_user(telegram_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/users/{telegram_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error fetching user: {e}")
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

async def create_order(user_id, product_id, order_type, mt5_id=None):
    async with httpx.AsyncClient() as client:
        try:
            payload = {
                "user_id": user_id,
                "product_id": product_id,
                "order_type": order_type
            }
            if mt5_id:
                payload["mt5_id"] = mt5_id
                
            response = await client.post(
                f"{BASE_URL}/orders/",
                json=payload
            )
            
            if response.status_code == 400:
                return {"error": response.json().get("detail", "Bad Request")}
                
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error creating order: {e}")
            return {"error": f"Connection Error: {str(e)}"}

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
            if response.status_code >= 400:
                return {"error": f"Payment API Error {response.status_code}: {response.text}"}
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error creating payment: {e}")
            return {"error": f"Payment Connection Error: {str(e)}"}

async def request_free_trial(telegram_id, mt5_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/trials/request",
                json={
                    "telegram_user_id": str(telegram_id),
                    "mt5_id": mt5_id
                }
            )
            
            if response.status_code >= 400:
                err_detail = "Failed to request trial."
                try:
                    err_detail = response.json().get("detail", err_detail)
                except:
                    pass
                return {"error": err_detail}
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error requesting free trial: {e}")
            return {"error": f"Connection Error: {str(e)}"}
