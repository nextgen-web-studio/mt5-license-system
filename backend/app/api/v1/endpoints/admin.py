from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.db.database import get_db
from app.models import User, Order, Payment, CompileJob, License, Product, VpsOrder

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
    usd_inr = 84.0
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get("https://open.er-api.com/v6/latest/USD")
            if res.status_code == 200:
                usd_inr = float(res.json()["rates"]["INR"])
    except Exception:
        pass

    # One time revenue: sum of product prices for delivered/paid one-time orders
    one_time_revenue = 0
    res_orders = await db.execute(
        select(Product.price, Product.type)
        .join(Order, Order.product_id == Product.id)
        .filter(Order.status.in_(["delivered", "paid", "active", "completed"]))
        .filter(Order.installment_enabled == False)
    )
    for price, p_type in res_orders:
        if p_type == 'EA':
            one_time_revenue += int(price * usd_inr)
        else:
            one_time_revenue += price
            
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
    result = await db.execute(select(CompileJob).order_by(CompileJob.created_at.desc()))
    jobs = result.scalars().all()
    return jobs

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Reset a failed or stuck compile job back to 'pending' so the worker
    can claim and process it again on the next poll cycle.
    """
    from fastapi import HTTPException
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

    await db.commit()

    return {
        "status": "success",
        "message": f"Job {job_id} reset from '{previous_status}' to 'pending'",
        "job_id": job_id
    }

@router.get("/all_orders")
async def get_all_orders_admin(db: AsyncSession = Depends(get_db)):
    usd_inr = 84.0
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            res = await client.get("https://open.er-api.com/v6/latest/USD")
            if res.status_code == 200:
                usd_inr = float(res.json()["rates"]["INR"])
    except Exception:
        pass

    result = await db.execute(
        select(Order, Product, User)
        .join(Product, Order.product_id == Product.id)
        .join(User, Order.user_id == User.id)
        .order_by(Order.created_at.desc())
    )
    rows = result.all()
    orders = []
    for order, product, user in rows:
        amount = int(product.price * usd_inr) if product.type == 'EA' else product.price
        orders.append({
            "id": order.id,
            "product": product.name,
            "customer": user.name or user.username or "Unknown",
            "amount": amount,
            "status": order.status,
            "date": order.created_at
        })
    return orders

from fastapi import HTTPException
from pydantic import BaseModel
import httpx
import os

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
            "screenshot_received": getattr(vps, 'screenshot_received', False) or False
        })
    return orders

@router.post("/vps-orders/{vps_id}/provision")
async def provision_vps(vps_id: int, data: VpsProvisionData, db: AsyncSession = Depends(get_db)):
    # 1. Update VpsOrder — allow re-provisioning (resend details)
    result = await db.execute(select(VpsOrder).filter(VpsOrder.id == vps_id))
    vps_order = result.scalar_one_or_none()
    if not vps_order:
        raise HTTPException(status_code=404, detail="VPS Order not found")
    
    # Always update fields (even if already provisioned — admin may be correcting details)
    vps_order.hostname = data.hostname
    vps_order.ip = data.ip
    vps_order.username = data.username
    vps_order.password = data.password
    
    # Fetch product to calculate auto expiry
    order_result = await db.execute(select(Order, Product).join(Product, Order.product_id == Product.id).filter(Order.id == vps_order.order_id))
    order_data = order_result.first()
    
    from datetime import datetime, timezone
    from dateutil.relativedelta import relativedelta
    
    if not vps_order.purchased_date:
        vps_order.purchased_date = datetime.now(timezone.utc)
        
    if not vps_order.expiry_date and order_data and order_data.Product:
        vps_order.expiry_date = vps_order.purchased_date + relativedelta(months=order_data.Product.duration)
        
    vps_order.status = "provisioned" 
    product_name = "VPS Package"
    if order_data:
        order, product = order_data
        order.status = "delivered"
        if product:
            product_name = product.name
    
    # Commit DB first — this always succeeds regardless of Telegram outcome
    await db.commit()
    
    # 3. Notify user via Telegram — wrapped in try/except so DB success is not rolled back
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
                    "🎉 *Your VPS is Ready!*\n\n"
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
        # VPS IS provisioned in DB — just notify admin that Telegram failed
        return {"status": "success", "warning": f"VPS provisioned successfully but Telegram notification failed: {telegram_error}"}
    
    return {"status": "success"}

@router.get("/run-migrations")
async def run_migrations():
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
    
    if old_status != "paid" and data.status == "paid":
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
                        raise HTTPException(status_code=500, detail=f"Telegram API Error: {res.text}")
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"Failed to reach Telegram API: {str(e)}")
                        
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
        "ALTER TABLE vps_orders ADD COLUMN hostname VARCHAR;",
        "ALTER TABLE vps_orders ADD COLUMN purchased_date TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE vps_orders ADD COLUMN expiry_date TIMESTAMP WITH TIME ZONE;",
        "ALTER TABLE users ADD COLUMN email VARCHAR;",
        "ALTER TABLE users ADD COLUMN location VARCHAR;",
        "ALTER TABLE users ADD COLUMN age VARCHAR;",
        "ALTER TABLE users ADD COLUMN occupation VARCHAR;",
        "ALTER TABLE orders ADD COLUMN vps_id INTEGER REFERENCES vps_orders(id);"
    ]
    results = []
    for q in queries:
        try:
            await db.execute(sa.text(q))
            results.append({"query": q, "status": "success"})
        except Exception as e:
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
            results.append({"query": q, "status": "success"})
        except Exception as e:
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
