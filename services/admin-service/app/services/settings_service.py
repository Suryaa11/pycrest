from datetime import datetime
from app.database.mongo import get_db

DEFAULT_SETTINGS = {
    "personal_loan_interest": 12.0,
    "vehicle_loan_interest": 10.0,
    "education_loan_interest": 11.0,
    "home_loan_interest": 8.5,
    "min_cibil_required": 650,
}


async def get_settings():
    db = await get_db()
    s = await db.system_settings.find_one({})
    if not s:
        s = {**DEFAULT_SETTINGS, "updated_by": None, "updated_at": datetime.utcnow()}
        await db.system_settings.insert_one(s)
    else:
        missing_defaults = {k: v for k, v in DEFAULT_SETTINGS.items() if s.get(k) is None}
        if missing_defaults:
            await db.system_settings.update_one({}, {"$set": missing_defaults})
            s = {**s, **missing_defaults}
    # stringify _id if present to avoid ObjectId serialization errors
    if s and "_id" in s:
        s["_id"] = str(s["_id"])
    return s

async def update_settings(admin_id: str, payload: dict):
    db = await get_db()
    await db.system_settings.update_one({}, {"$set": {**payload, "updated_by": admin_id, "updated_at": datetime.utcnow()}}, upsert=True)
    return await get_settings()
