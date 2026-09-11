from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.database import get_db
from app.models import User, Order, Payment, CompileJob, License, Product, VpsOrder, BrokerChangeRequest

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # Total Users
    result = await db.execute(select(func.count()).select_from(User))
    total_users = result.scalar() or 0

    # Total Orders
    result = await db.execute(select(func.count()).select_from(Order))
    total_orders = result.scalar() or 0

    # Fetch live USD to INR rate
    global _cached_usd_inr, _last_usd_fetch
    import time, asyncio, httpx
    if '_cached_usd_inr' not in globals():
        _cached_usd_inr = 84.0
        _last_usd_fetch = 0
    
    # Only fetch once per hour to avoid lagging the dashboard
    if time.time() - _last_usd_fetch > 3600:
        _last_usd_fetch = time.time() # Immediately mark as fetched to prevent stampede
        async def fetch_usd():
            global _cached_usd_inr
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.get("https://open.er-api.com/v6/latest/USD")
                    if res.status_code == 200:
                        _cached_usd_inr = float(res.json()["rates"]["INR"])
            except Exception:
                pass
        asyncio.create_task(fetch_usd())
            
    usd_inr = _cached_usd_inr

    # Fetch all offers for historical pricing
    from app.models import Offer
    from datetime import timezone
    offer_result = await db.execute(select(Offer))
    all_offers = offer_result.scalars().all()

    # One time revenue: sum of product prices for delivered/paid one-time orders
    one_time_revenue = 0
    res_orders = await db.execute(
        select(Order, Product)
        .join(Order, Order.product_id == Product.id)
        .filter(Order.status.in_(["delivered", "paid", "active", "completed"]))
        .filter(Order.installment_enabled == False)
    )
    for order, product in res_orders:
        base_price = product.price
        order_time = order.created_at
        if order_time and order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
            
        for o in all_offers:
            if o.product_id == product.id and o.active:
                starts = o.starts_at if o.starts_at.tzinfo else o.starts_at.replace(tzinfo=timezone.utc)
                expires = o.expires_at if o.expires_at.tzinfo else o.expires_at.replace(tzinfo=timezone.utc)
                if order_time and starts <= order_time <= expires:
                    base_price = o.offer_price
                    break

        if product.type == 'EA':
            one_time_revenue += int(base_price * usd_inr)
        else:
            one_time_revenue += int(base_price)
            
    # Installment revenue
    from app.models import InstallmentPayment
    result2 = await db.execute(select(func.sum(InstallmentPayment.amount)))
    installment_revenue = result2.scalar() or 0
    
    total_revenue = one_time_revenue + installment_revenue

    # Active Licenses
    result = await db.execute(select(func.count()).select_from(License).filter(License.status.in_(["active", "valid"])))
    active_licenses = result.scalar() or 0

    # Compiler Queue (pending jobs)
    result = await db.execute(select(func.count()).select_from(CompileJob).filter(CompileJob.status == "pending"))
    compiler_queue = result.scalar() or 0
    
    # Recent Orders
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(5))
    recent_orders = result.scalars().all()

    return {
        "total_users": total_users,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "active_licenses": active_licenses,
        "compiler_queue": compiler_queue,
        "recent_orders": [
            {
                "id": o.id,
                "product_id": o.product_id,
                "user_id": o.user_id,
                "status": o.status,
                "created_at": o.created_at
            }
            for o in recent_orders
        ]
    }

@router.get("/compiler_jobs")
async def get_compiler_jobs(db: AsyncSession = Depends(get_db)):
    from app.models import License
    query = (
        select(CompileJob, License.order_id)
        .outerjoin(License, CompileJob.license_id == License.id)
        .order_by(CompileJob.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    jobs = []
    for job, order_id in rows:
        job_dict = {c.name: getattr(job, c.name) for c in job.__table__.columns}
        job_dict["order_id"] = order_id
        jobs.append(job_dict)
    return jobs

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """
    Reset a failed or stuck compile job back to 'pending' and trigger the local wine compiler.
    """
    from fastapi import HTTPException
    from app.core.local_compiler import local_wine_compiler
    
    result = await db.execute(select(CompileJob).filter(CompileJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.status not in ("failed", "processing"):
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is '{job.status}' — can only retry 'failed' or stuck 'processing' jobs"
        )

    previous_status = job.status
    job.status       = "pending"
    job.error_message = None
    job.worker_id    = None
    job.started_at   = None
    job.completed_at = None

    # If it is tied to a license, also set license status
    if job.license_id:
        from app.models import License, User
        lic_res = await db.execute(select(License).filter(License.id == job.license_id))
        lic = lic_res.scalar_one_or_none()
        if lic:
            lic.status = "compiling"
            await db.commit()
            
            # Send animated TG notification
            import os
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            user_res = await db.execute(select(User).filter(User.id == lic.user_id))
            user = user_res.scalar_one_or_none()
            if bot_token and user and user.telegram_id:
                from app.core.telegram_animator import start_compile_and_animate
                start_compile_and_animate(background_tasks, job.id, bot_token, user.telegram_id, lic.id, None)
                return {"status": "success", "message": f"Job {job_id} requeued and customer notified."}

    await db.commit()
    
    # Trigger the compiler immediately
    background_tasks.add_task(local_wine_compiler, job.id)

    return {
        "status": "success",
        "message": f"Job {job_id} reset from '{previous_status}' to 'pending' and compiler started",
        "job_id": job_id
    }

@router.get("/all_orders")
async def get_all_orders_admin(db: AsyncSession = Depends(get_db)):
    global _cached_usd_inr, _last_usd_fetch
    import time, asyncio, httpx
    if '_cached_usd_inr' not in globals():
        _cached_usd_inr = 84.0
        _last_usd_fetch = 0
    
    # Only fetch once per hour to avoid lagging the dashboard
    if time.time() - _last_usd_fetch > 3600:
        _last_usd_fetch = time.time() # Immediately mark as fetched to prevent stampede
        async def fetch_usd():
            global _cached_usd_inr
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    res = await client.get("https://open.er-api.com/v6/latest/USD")
                    if res.status_code == 200:
                        _cached_usd_inr = float(res.json()["rates"]["INR"])
            except Exception:
                pass
        asyncio.create_task(fetch_usd())
            
    usd_inr = _cached_usd_inr

    from app.models import Offer
    from datetime import timezone
    offer_result = await db.execute(select(Offer))
    all_offers = offer_result.scalars().all()

    result = await db.execute(
        select(Order, Product, User)
        .join(Product, Order.product_id == Product.id)
        .join(User, Order.user_id == User.id)
        .order_by(Order.created_at.desc())
    )
    rows = result.all()
    orders = []
    for order, product, user in rows:
        base_price = product.price
        order_time = order.created_at
        if order_time and order_time.tzinfo is None:
            order_time = order_time.replace(tzinfo=timezone.utc)
        
        for o in all_offers:
            if o.product_id == product.id and o.active:
                starts = o.starts_at if o.starts_at.tzinfo else o.starts_at.replace(tzinfo=timezone.utc)
                expires = o.expires_at if o.expires_at.tzinfo else o.expires_at.replace(tzinfo=timezone.utc)
                if order_time and starts <= order_time <= expires:
                    base_price = o.offer_price
                    break

        amount = int(base_price * usd_inr) if product.type == 'EA' else int(base_price)
        orders.append({
            "id": order.id,
            "product": product.name,
            "customer": user.name or user.username or "Unknown",
            "amount": amount,
            "status": order.status,
            "date": order.created_at,
            "is_renewal": bool(order.vps_id) and product.type == "VPS",
            "order_type": order.order_type,
            "mt5_id": getattr(order, 'mt5_id', None),
            "is_broker_change": False
        })
        
    # Fetch broker change requests
    
    bc_result = await db.execute(
        select(BrokerChangeRequest, License, Product, User)
        .join(License, BrokerChangeRequest.license_id == License.id)
        .join(Order, License.order_id == Order.id)
        .join(Product, Order.product_id == Product.id)
        .join(User, BrokerChangeRequest.user_id == User.id)
        .order_by(BrokerChangeRequest.created_at.desc())
    )
    bc_rows = bc_result.all()
    for req, lic, product, user in bc_rows:
        orders.append({
            "id": f"BC-{req.id}",
            "real_id": req.id,
            "product": f"BROKER CHANGE ({product.name})",
            "customer": user.name or user.username or "Unknown",
            "amount": 0,
            "status": req.status,
            "date": req.created_at,
            "is_renewal": False,
            "mt5_id": f"{lic.mt5_id} -> {req.new_mt5_id}",
            "is_broker_change": True
        })
        
    orders.sort(key=lambda x: x["date"], reverse=True)
    return orders

from fastapi import HTTPException
from pydantic import BaseModel
import httpx
import os
import asyncio

class VpsStatusUpdate(BaseModel):
    status: str

class VpsMessageData(BaseModel):
    message: str

class VpsProvisionData(BaseModel):
    hostname: Optional[str] = None
    ip: str
    username: str
    password: str
    purchased_date: Optional[str] = None
    expiry_date: Optional[str] = None

@router.get("/vps-orders")
async def get_vps_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VpsOrder, Order, User, Product)
        .join(Order, VpsOrder.order_id == Order.id)
        .join(User, VpsOrder.user_id == User.id)
        .join(Product, Order.product_id == Product.id)
        .order_by(VpsOrder.created_at.desc())
    )
    
    orders = []
    for vps, order, user, product in result.all():
        orders.append({
            "id": vps.id,
            "order_id": order.id,
            "customer": user.name or user.username or "Unknown",
            "telegram_id": user.telegram_id,
            "plan_name": product.name,
            "duration": vps.duration,
            "status": vps.status,
            "ip": vps.ip,
            "hostname": vps.hostname,
            "username": vps.username,
            "purchased_date": vps.purchased_date,
            "expiry_date": vps.expiry_date,
            "created_at": vps.created_at,
            "screenshot_received": getattr(vps, 'screenshot_received', False) or False,
            "is_renewal": False
        })
        
    # Also fetch RENEWAL orders
    renewal_res = await db.execute(
        select(Order, User, Product, VpsOrder)
        .join(User, Order.user_id == User.id)
        .join(Product, Order.product_id == Product.id)
        .join(VpsOrder, Order.vps_id == VpsOrder.id)
        .filter(Order.order_type == "VPS")
        .filter(Order.vps_id.isnot(None))
    )
    for order, user, product, vps in renewal_res.all():
        orders.append({
            "id": vps.id,
            "order_id": order.id,
            "customer": user.name or user.username or "Unknown",
            "telegram_id": user.telegram_id,
            "plan_name": product.name,
            "duration": product.duration or 1,
            "status": order.status,
            "ip": vps.ip,
            "hostname": vps.hostname,
            "username": vps.username,
            "purchased_date": vps.purchased_date,
            "expiry_date": vps.expiry_date,
            "created_at": order.created_at,
            "screenshot_received": False,
            "is_renewal": True
        })
        
    orders.sort(key=lambda x: x["order_id"], reverse=True)
    return orders

LAST_VPS_ERROR = "No error logged yet."

@router.post("/vps-orders/{vps_id}/provision")
async def provision_vps(vps_id: int, data: VpsProvisionData, db: AsyncSession = Depends(get_db)):
    global LAST_VPS_ERROR
    try:
        # 1. Update VpsOrder - allow re-provisioning (resend details)
        result = await db.execute(select(VpsOrder).filter(VpsOrder.id == vps_id))
        vps_order = result.scalar_one_or_none()
        if not vps_order:
            raise HTTPException(status_code=404, detail="VPS Order not found")
        
        # Always update fields (even if already provisioned - admin may be correcting details)
        vps_order.hostname = data.hostname
        vps_order.ip = data.ip
        vps_order.username = data.username
        vps_order.password = data.password
        
        # Fetch product to calculate auto expiry
        order_result = await db.execute(select(Order, Product).join(Product, Order.product_id == Product.id).filter(Order.id == vps_order.order_id))
        order_data = order_result.first()
        
        order = None
        product = None
        if order_data:
            order, product = order_data
        
        from datetime import datetime, timezone
        from dateutil.relativedelta import relativedelta
        
        if not vps_order.purchased_date:
            vps_order.purchased_date = datetime.now(timezone.utc)
            
        if not vps_order.expiry_date and product:
            vps_order.expiry_date = vps_order.purchased_date + relativedelta(months=product.duration)
            
        vps_order.status = "provisioned" 
        product_name = "VPS Package"
        if order:
            order.status = "delivered"
        if product:
            product_name = product.name
        
        # Commit DB first - this always succeeds regardless of Telegram outcome
        await db.commit()
        
        # 3. Notify user via Telegram
        telegram_error = None
        try:
            user_result = await db.execute(select(User).filter(User.id == vps_order.user_id))
            user = user_result.scalar_one_or_none()
            
            if user and user.telegram_id:
                bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
                if bot_token:
                    from zoneinfo import ZoneInfo
                    def to_ist_str(dt):
                        if not dt: return "N/A"
                        if dt.tzinfo is None:
                            from datetime import timezone
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %I:%M %p IST")
                    p_date_str = to_ist_str(vps_order.purchased_date)
                    e_date_str = to_ist_str(vps_order.expiry_date)
                    
                    msg = (
                        "✅ *Your VPS is Ready!*\n\n"
                        "*VPS Node Details*\n"
                        f"Product Name: `{product_name}`\n"
                        f"Hostname: `{data.hostname or 'N/A'}`\n"
                        f"Main IP: `{data.ip}`\n"
                        f"User name: `{data.username}`\n"
                        f"Root password: `{data.password}`\n\n"
                        f"Purchased Date: `{p_date_str}`\n"
                        f"Expiry Date & Time: `{e_date_str}`\n\n"
                        "Please connect using Remote Desktop Connection (RDP) on your PC or phone.\n\n"
                        "📺 *VPS Setup Guide:* [Click here to watch the setup tutorial](https://youtube.com/shorts/eSWipdqtUso?si=qTOVSUf1fTezGqZR)"
                    )
                    import httpx
                    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": user.telegram_id,
                                "text": msg,
                                "parse_mode": "Markdown",
                                "disable_web_page_preview": True
                            }
                        )
                        if resp.status_code != 200:
                            telegram_error = f"Telegram API error: {resp.text}"
        except Exception as e:
            telegram_error = str(e)
        
        if telegram_error:
            return {"status": "success", "warning": f"VPS provisioned successfully but Telegram notification failed: {telegram_error}"}
        
        return {"status": "success"}
    except Exception as e:
        import traceback
        error_msg = f"CRITICAL CRASH: {str(e)}\n{traceback.format_exc()}"
        LAST_VPS_ERROR = error_msg
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/debug-error")
async def get_debug_error():
    return {"error": LAST_VPS_ERROR}

@router.get("/test-provision")
async def test_provision():
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://infinity-trader-docker-test.onrender.com/api/v1/admin/vps-orders/20/provision",
                json={"hostname": "test", "ip": "1.2.3.4", "username": "admin", "password": "pass"}
            )
            return {"status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"error": str(e)}
    import subprocess
    import sys
    try:
        result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], capture_output=True, text=True)
        return {"stdout": result.stdout, "stderr": result.stderr}
    except Exception as e:
        return {"error": str(e)}


@router.put("/vps-orders/{vps_id}/status")
async def update_vps_status(vps_id: int, data: VpsStatusUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VpsOrder).filter(VpsOrder.id == vps_id))
    vps_order = result.scalar_one_or_none()
    if not vps_order:
        raise HTTPException(status_code=404, detail="VPS Order not found")
        
    old_status = vps_order.status
    vps_order.status = data.status
    
    # Sync parent Order status
    order_res = await db.execute(select(Order).filter(Order.id == vps_order.order_id))
    parent_order = order_res.scalar_one_or_none()
    if parent_order:
        if data.status == "paid":
            parent_order.status = "approved"
        elif data.status == "contacted":
            parent_order.status = "contacted"
        elif data.status == "provisioned":
            parent_order.status = "delivered"
        else:
            parent_order.status = data.status
            
    await db.commit()
    
    if old_status != "rejected" and data.status == "rejected":
        import os, httpx, asyncio
        bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com")
        bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
        bot_webhook_url += "/internal/order-rejected"
        try:
            async def trigger_clear_buttons():
                async with httpx.AsyncClient(verify=False) as client:
                    await client.post(bot_webhook_url, json={"order_id": vps_order.order_id})
            asyncio.create_task(trigger_clear_buttons())
        except Exception:
            pass

        # Send rejection notification
        user_result = await db.execute(select(User).filter(User.id == vps_order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.telegram_id:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            if bot_token:
                try:
                    async def notify_user():
                        async with httpx.AsyncClient(verify=False) as client:
                            await client.post(
                                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                                json={
                                    "chat_id": user.telegram_id,
                                    "text": f"❌ <b>VPS ORDER REJECTED</b>\n\nUnfortunately, your VPS order (ORD-{vps_order.order_id}) has been rejected by the admin. Please contact support for more details.",
                                    "parse_mode": "HTML"
                                }
                            )
                    asyncio.create_task(notify_user())
                except Exception:
                    pass

    if old_status != "paid" and data.status == "paid":
        import os, httpx, asyncio
        bot_webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL", "https://infinity-trader-telegram-bot-6gf3.onrender.com")
        bot_webhook_url = bot_webhook_url.replace("/internal/delivery", "").replace("/internal/compile-started", "").replace("/internal/order-approved", "").replace("/bot", "").rstrip("/")
        bot_webhook_url += "/internal/order-approved"
        try:
            async def trigger_clear_buttons():
                async with httpx.AsyncClient(verify=False) as client:
                    await client.post(bot_webhook_url, json={"order_id": vps_order.order_id})
            asyncio.create_task(trigger_clear_buttons())
        except Exception:
            pass

        user_result = await db.execute(select(User).filter(User.id == vps_order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.telegram_id:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not bot_token:
                raise HTTPException(status_code=500, detail="Backend missing TELEGRAM_BOT_TOKEN environment variable!")
                
            msg = (
                f"✅ *PAYMENT SUCCESSFUL*\n\n"
                f"Your payment for VPS Order #ORD-{vps_order.order_id} has been verified by the Admin.\n\n"
                f"Your VPS node is currently being prepared and provisioned. "
                f"You will receive your login details (IP and Password) here shortly!"
            )
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                try:
                    res = await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                    )
                    if res.status_code != 200:
                        print(f"Telegram error: {res.text}")
                except Exception as e:
                    print(f"Telegram error: {e}")
                        
    return {"status": "success", "new_status": vps_order.status}

@router.post("/vps-orders/{vps_id}/message")
async def send_vps_message(vps_id: int, data: VpsMessageData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VpsOrder).filter(VpsOrder.id == vps_id))
    vps_order = result.scalar_one_or_none()
    if not vps_order:
        raise HTTPException(status_code=404, detail="VPS Order not found")
        
    user_result = await db.execute(select(User).filter(User.id == vps_order.user_id))
    user = user_result.scalar_one_or_none()
    
    if not user or not user.telegram_id:
        raise HTTPException(status_code=400, detail="User Telegram ID not found")
        
    import os
    import httpx
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    msg_text = f"📩 **Message from Admin regarding your VPS Order:**\n\n{data.message}"
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": user.telegram_id,
                    "text": msg_text,
                    "parse_mode": "Markdown"
                }
            )
            if resp.status_code != 200:
                print(f"Telegram error: {resp.text}")
    except Exception as e:
        print(f"Failed to send telegram msg: {e}")
        
    return {"status": "success", "message": "Message sent to customer"}

@router.put("/vps-orders/by-order/{order_id}/paid")
async def mark_vps_paid_by_order(order_id: int, db: AsyncSession = Depends(get_db)):
    # 1. Update the parent order
    order_res = await db.execute(select(Order).filter(Order.id == order_id))
    order = order_res.scalar_one_or_none()
    if order:
        order.status = "paid"
        
    # 2. Update the vps order
    result = await db.execute(select(VpsOrder).filter(VpsOrder.order_id == order_id))
    vps_order = result.scalar_one_or_none()
    if not vps_order:
        raise HTTPException(status_code=404, detail="VPS Order not found")
        
    old_status = vps_order.status
    vps_order.status = "paid"
    await db.commit()
    
    # 3. Notify user
    if old_status != "paid":
        user_result = await db.execute(select(User).filter(User.id == vps_order.user_id))
        user = user_result.scalar_one_or_none()
        if user and user.telegram_id:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            if not bot_token:
                raise HTTPException(status_code=500, detail="Backend missing TELEGRAM_BOT_TOKEN environment variable!")
            msg = (
                f"✅ *PAYMENT SUCCESSFUL*\n\n"
                f"Your payment for VPS Order #ORD-{order_id} has been received and verified.\n\n"
                f"Your VPS node is currently being prepared and provisioned. "
                f"You will receive your login details (IP and Password) here shortly!"
            )
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                try:
                    res = await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": user.telegram_id, "text": msg, "parse_mode": "Markdown"}
                    )
                    if res.status_code != 200:
                        raise HTTPException(status_code=500, detail=f"Telegram API Error: {res.text}")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to reach Telegram API: {str(e)}")
    return {"status": "success"}

@router.get("/force-migration")
async def force_migration(db: AsyncSession = Depends(get_db)):
    import sqlalchemy as sa
    queries = [
        "UPDATE orders SET vps_id = 4 WHERE id = 16",
        "UPDATE orders SET vps_id = 7 WHERE id = 14",
        "UPDATE orders SET vps_id = 7 WHERE id = 12",
        "UPDATE orders SET vps_id = 7 WHERE id = 11"
    ]
    results = []
    for q in queries:
        try:
            await db.execute(sa.text(q))
            await db.commit()
            results.append({"query": q, "status": "success"})
        except Exception as e:
            await db.rollback()
            results.append({"query": q, "status": "skipped", "reason": str(e)})
    
    # Try updating alembic version table so it knows we are up to date
    try:
        await db.execute(sa.text("UPDATE alembic_version SET version_num='e6c0208380g1'"))
    except Exception:
        pass
        
    await db.commit()
    return {"results": results}

@router.get("/vps-orders/force-screenshot-migration")
async def force_screenshot_migration(db: AsyncSession = Depends(get_db)):
    import sqlalchemy as sa
    queries = [
        "ALTER TABLE vps_orders ADD COLUMN screenshot_received BOOLEAN DEFAULT FALSE;",
        "ALTER TABLE vps_orders ADD COLUMN screenshot_file_id VARCHAR;",
        "ALTER TABLE orders ADD COLUMN vps_id INTEGER REFERENCES vps_orders(id);"
    ]
    results = []
    for q in queries:
        try:
            await db.execute(sa.text(q))
            await db.commit()
            results.append({"query": q, "status": "success"})
        except Exception as e:
            await db.rollback()
            results.append({"query": q, "status": "skipped", "reason": str(e)})
    await db.commit()
    return {"results": results}

@router.post("/vps-orders/by-order/{order_id}/screenshot")
async def mark_vps_screenshot_received(order_id: int, db: AsyncSession = Depends(get_db)):
    import sqlalchemy as sa
    try:
        await db.execute(
            sa.text("UPDATE vps_orders SET screenshot_received = TRUE WHERE order_id = :oid"),
            {"oid": order_id}
        )
        await db.commit()
    except Exception:
        pass
    return {"status": "success"}


@router.get("/trigger-vps-reminders")
async def trigger_vps_reminders():
    """Manually trigger the VPS expiry reminder cron job for testing."""
    from app.cron.vps_reminders import run_vps_reminders
    await run_vps_reminders(force_test=True)
    return {"status": "done", "message": "VPS reminders job executed. Check your Telegram for notifications."}

@router.get("/vps-orders/{vps_id}/info")
async def get_vps_info(vps_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy.future import select
    from app.models import VpsOrder, Order, Product
    result = await db.execute(select(VpsOrder, Order, Product).join(Order, VpsOrder.order_id == Order.id).join(Product, Order.product_id == Product.id).filter(VpsOrder.id == vps_id))
    row = result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="VPS not found")
    vps, order, prod = row
    return {
        "id": vps.id,
        "product_id": prod.id,
        "product_name": prod.name,
        "product_price": prod.price
    }
class BotMessageMapData(BaseModel):
    key: str
    message_id: int

@router.post("/bot-message-map")
async def save_bot_message_map(data: BotMessageMapData, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    await db.execute(
        text("INSERT INTO bot_message_map (key, message_id) VALUES (:key, :message_id) ON CONFLICT (key) DO UPDATE SET message_id = EXCLUDED.message_id"),
        {"key": data.key, "message_id": data.message_id}
    )
    await db.commit()
    return {"status": "success"}

@router.get("/bot-message-map/{key}")
async def get_bot_message_map(key: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    res = await db.execute(text("SELECT message_id FROM bot_message_map WHERE key = :key"), {"key": key})
    row = res.fetchone()
    if row:
        return {"message_id": row[0]}
    return {"message_id": None}

@router.delete("/bot-message-map/{key}")
async def delete_bot_message_map(key: str, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    await db.execute(text("DELETE FROM bot_message_map WHERE key = :key"), {"key": key})
    await db.commit()
    return {"status": "success"}
