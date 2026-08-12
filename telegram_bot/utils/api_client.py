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

async def update_user_phone(user_id, phone):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(f"{BASE_URL}/users/{user_id}/phone", json={"phone": phone})
            if response.status_code >= 400:
                return False
            return True
        except Exception as e:
            logging.error(f"Error updating phone: {e}")
            return False

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

async def approve_order(order_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/orders/{order_id}/approve")
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error approving order: {e}")
            return {"error": str(e)}

async def reject_order(order_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/orders/{order_id}/reject")
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error rejecting order: {e}")
            return {"error": str(e)}

async def generate_license(order_id, mt5_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/licenses/generate",
                json={
                    "order_id": order_id,
                    "mt5_id": mt5_id
                }
            )
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error generating license: {e}")
            return {"error": str(e)}

async def save_order_mt5_id(order_id, mt5_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{BASE_URL}/orders/{order_id}/mt5",
                json={
                    "mt5_id": mt5_id
                }
            )
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error saving MT5 ID: {e}")
            return {"error": str(e)}

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

async def request_broker_change(license_id, new_mt5_id, new_broker, telegram_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/licenses/{license_id}/broker-change-request",
                json={"new_mt5_id": new_mt5_id, "new_broker": new_broker, "telegram_id": str(telegram_id)}
            )
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error requesting broker change: {e}")
            return {"error": str(e)}

async def approve_broker_change(request_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/licenses/broker-change/{request_id}/approve")
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error approving broker change: {e}")
            return {"error": str(e)}

async def reject_broker_change(request_id):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/licenses/broker-change/{request_id}/reject")
            if response.status_code >= 400:
                return {"error": f"API Error {response.status_code}: {response.text}"}
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Error rejecting broker change: {e}")
            return {"error": str(e)}

async def get_settings():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/settings/")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception:
            return {}

async def update_setting(key, value):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(f"{BASE_URL}/settings/{key}", json={"setting_value": str(value)})
            if response.status_code == 200:
                return True
            return False
        except Exception:
            return False
