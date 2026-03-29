from datetime import datetime
from fastapi import HTTPException
from app.database.mongo import get_db
from app.core.security import hash_password
from app.models.enums import Roles
from app.utils.id import user_id_filter
from app.utils.sequences import next_customer_id
from app.utils.serializers import normalize_doc

async def list_users(limit: int = 500):
    db = await get_db()
    users = await db.staff_users.find({}, {"password": 0}).sort("created_at", -1).to_list(length=limit)
    return [normalize_doc(u) for u in users]

async def set_user_status(user_id: str, is_active: bool):
    db = await get_db()
    filt = user_id_filter(user_id)
    await db.staff_users.update_one(filt, {"$set": {"is_active": bool(is_active), "updated_at": datetime.utcnow()}})
    user = await db.staff_users.find_one(filt, {"password": 0})
    return normalize_doc(user)

async def create_staff_user(email: str, full_name: str, password: str, role: str, **kwargs):
    if role not in [Roles.ADMIN, Roles.MANAGER, Roles.VERIFICATION]:
        raise HTTPException(status_code=400, detail="Invalid role")
    db = await get_db()
    if await db.staff_users.find_one({"email": email}) or await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    doc = {
        "full_name": full_name,
        "email": email,
        "password": hash_password(password),
        "role": role,
        "_id": await next_customer_id(),
        "is_active": True,
        "created_at": datetime.utcnow(),
        **{k: (v.strip() if isinstance(v, str) else v) for k, v in kwargs.items() if v is not None}
    }
    await db.staff_users.insert_one(doc)
    return normalize_doc(doc)

async def update_staff_user(user_id: str, payload: dict):
    db = await get_db()
    filt = user_id_filter(user_id)
    update_dict = {k: v for k, v in payload.items() if v is not None}
    if "password" in update_dict:
        update_dict["password"] = hash_password(update_dict["password"])
    update_dict["updated_at"] = datetime.utcnow()
    await db.staff_users.update_one(filt, {"$set": update_dict})
    return normalize_doc(await db.staff_users.find_one(filt, {"password": 0}))

async def delete_staff_user(user_id: str):
    db = await get_db()
    result = await db.staff_users.delete_one(user_id_filter(user_id))
    return {"success": result.deleted_count > 0}
