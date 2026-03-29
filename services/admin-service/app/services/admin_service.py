from app.database.mongo import get_db
from app.models.enums import LoanStatus
from app.utils.id import loan_id_filter, user_id_filter


def _mask_pan(value: str | None) -> str | None:
    pan = str(value or "").strip().upper()
    if not pan:
        return None
    if len(pan) != 10:
        return pan
    return f"{pan[:2]}******{pan[-2:]}"


def _sanitize_loan_doc(doc: dict) -> dict:
    from app.utils.serializers import normalize_doc

    out = normalize_doc(doc)
    if not out.get("pan_masked"):
        out["pan_masked"] = _mask_pan(out.get("pan_number"))
    if not out.get("guarantor_pan_masked"):
        out["guarantor_pan_masked"] = _mask_pan(out.get("guarantor_pan"))

    out.pop("pan_number", None)
    out.pop("guarantor_pan", None)
    out.pop("pan_hash", None)
    out.pop("guarantor_pan_hash", None)
    return out


async def get_admin_approvals_dashboard(days: int = 30):
    db = await get_db()
    from datetime import datetime, timedelta
    from app.utils.serializers import normalize_doc

    admin_queue_statuses = [
        LoanStatus.PENDING_ADMIN_APPROVAL,
        LoanStatus.MANAGER_APPROVED,
        LoanStatus.ADMIN_APPROVED,
        LoanStatus.SANCTION_SENT,
        LoanStatus.SIGNED_RECEIVED,
        LoanStatus.READY_FOR_DISBURSEMENT,
    ]

    pending = await db.personal_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    pending += await db.vehicle_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    pending += await db.education_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    pending += await db.home_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)

    cutoff = datetime.utcnow() - timedelta(days=int(days or 30))
    processed_statuses = [
        LoanStatus.ACTIVE,
        LoanStatus.COMPLETED,
        LoanStatus.FORECLOSED,
        LoanStatus.REJECTED,
    ]

    processed_filter = {
        "status": {"$in": processed_statuses},
        "$or": [
            {"disbursed_at": {"$gte": cutoff}},
            {"rejected_at": {"$gte": cutoff}},
            {"foreclosed_at": {"$gte": cutoff}},
            {"approved_at": {"$gte": cutoff}},
            {"applied_at": {"$gte": cutoff}},
        ],
    }

    processed = await db.personal_loans.find(processed_filter).sort("applied_at", -1).to_list(length=200)
    processed += await db.vehicle_loans.find(processed_filter).sort("applied_at", -1).to_list(length=200)
    processed += await db.education_loans.find(processed_filter).sort("applied_at", -1).to_list(length=200)
    processed += await db.home_loans.find(processed_filter).sort("applied_at", -1).to_list(length=200)

    return {
        "pending_approvals": [_sanitize_loan_doc(l) for l in pending],
        "processed_approvals": [_sanitize_loan_doc(l) for l in processed],
        "cutoff_days": int(days or 30),
    }


async def list_pending_admin_approvals():
    db = await get_db()
    admin_queue_statuses = [
        LoanStatus.PENDING_ADMIN_APPROVAL,
        LoanStatus.MANAGER_APPROVED,
        LoanStatus.ADMIN_APPROVED,
        LoanStatus.SANCTION_SENT,
        LoanStatus.SIGNED_RECEIVED,
        LoanStatus.READY_FOR_DISBURSEMENT,
    ]
    loans = await db.personal_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    loans += await db.vehicle_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    loans += await db.education_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    loans += await db.home_loans.find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]


async def find_loan_any(loan_id: str):
    db = await get_db()
    filt = loan_id_filter(loan_id)

    loan = await db.personal_loans.find_one(filt)
    if loan:
        return "personal_loans", loan

    loan = await db.vehicle_loans.find_one(filt)
    if loan:
        return "vehicle_loans", loan

    loan = await db.education_loans.find_one(filt)
    if loan:
        return "education_loans", loan

    loan = await db.home_loans.find_one(filt)
    if loan:
        return "home_loans", loan

    return None, None


async def list_high_value_pending():
    db = await get_db()
    filt = {"status": LoanStatus.PENDING_ADMIN_APPROVAL, "loan_amount": {"$gt": 1500000}}
    loans = await db.personal_loans.find(filt).to_list(length=200)
    loans += await db.vehicle_loans.find(filt).to_list(length=200)
    loans += await db.education_loans.find(filt).to_list(length=200)
    loans += await db.home_loans.find(filt).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]


async def list_ready_for_disbursement():
    db = await get_db()
    filt = {"status": LoanStatus.READY_FOR_DISBURSEMENT}
    loans = await db.personal_loans.find(filt).to_list(length=200)
    loans += await db.vehicle_loans.find(filt).to_list(length=200)
    loans += await db.education_loans.find(filt).to_list(length=200)
    loans += await db.home_loans.find(filt).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]


from datetime import datetime
from fastapi import HTTPException
from app.core.security import hash_password
from app.models.enums import Roles
from app.utils.sequences import next_customer_id


async def list_users(limit: int = 500):
    db = await get_db()
    users = await db.staff_users.find({}, {"password": 0}).sort("created_at", -1).to_list(length=limit)
    from app.utils.serializers import normalize_doc
    return [normalize_doc(u) for u in users]


async def set_user_status(user_id: str, is_active: bool):
    db = await get_db()
    filt = user_id_filter(user_id)

    user = await db.staff_users.find_one(filt, {"password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Staff user not found")

    await db.staff_users.update_one(
        filt,
        {"$set": {"is_active": bool(is_active), "updated_at": datetime.utcnow()}},
    )

    user = await db.staff_users.find_one(filt, {"password": 0})
    from app.utils.serializers import normalize_doc
    return normalize_doc(user)


async def create_staff_user(
    email: str,
    full_name: str,
    password: str,
    role: str,
    phone: str | None = None,
    department: str | None = None,
    designation: str | None = None,
    employee_code: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
):
    if role not in [Roles.ADMIN, Roles.MANAGER, Roles.VERIFICATION]:
        raise HTTPException(status_code=400, detail="Invalid role")
    db = await get_db()
    existing_customer = await db.users.find_one({"email": email})
    existing_staff = await db.staff_users.find_one({"email": email})
    if existing_customer or existing_staff:
        raise HTTPException(status_code=400, detail="Email already exists")
    doc = {
        "full_name": full_name,
        "email": email,
        "password": hash_password(password),
        "role": role,
        "phone": (phone or "").strip() or None,
        "department": (department or "").strip() or None,
        "designation": (designation or "").strip() or None,
        "employee_code": (employee_code or "").strip() or None,
        "address": (address or "").strip() or None,
        "city": (city or "").strip() or None,
        "state": (state or "").strip() or None,
        "country": (country or "").strip() or None,
        "_id": await next_customer_id(),
        "is_active": True,
        "created_at": datetime.utcnow(),
    }
    res = await db.staff_users.insert_one(doc)
    from app.utils.serializers import normalize_doc
    out = {"_id": doc["_id"], **doc}
    return normalize_doc(out)


async def update_staff_user(user_id: str, payload: dict):
    """Update staff user details. Allows updating full_name, email, password, role, is_active."""
    db = await get_db()
    filt = user_id_filter(user_id)
    
    user = await db.staff_users.find_one(filt, {"password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Staff user not found")
    
    update_dict = {}
    
    if "full_name" in payload and payload["full_name"]:
        update_dict["full_name"] = payload["full_name"]
    
    if "email" in payload and payload["email"]:
        # Check if email is already in use by another user
        existing_customer = await db.users.find_one({"email": payload["email"]})
        existing_staff = await db.staff_users.find_one({"email": payload["email"], "_id": {"$ne": user["_id"]}})
        if existing_customer or existing_staff:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_dict["email"] = payload["email"]
    
    if "password" in payload and payload["password"]:
        update_dict["password"] = hash_password(payload["password"])
    
    if "role" in payload and payload["role"]:
        if payload["role"] not in [Roles.ADMIN, Roles.MANAGER, Roles.VERIFICATION]:
            raise HTTPException(status_code=400, detail="Invalid role")
        update_dict["role"] = payload["role"]
    
    if "is_active" in payload and payload["is_active"] is not None:
        update_dict["is_active"] = bool(payload["is_active"])

    for field in ["phone", "department", "designation", "employee_code", "address", "city", "state", "country"]:
        if field in payload:
            value = payload.get(field)
            if isinstance(value, str):
                update_dict[field] = value.strip() or None
            else:
                update_dict[field] = value
    
    update_dict["updated_at"] = datetime.utcnow()
    
    await db.staff_users.update_one(filt, {"$set": update_dict})
    updated = await db.staff_users.find_one(filt, {"password": 0})
    from app.utils.serializers import normalize_doc
    return normalize_doc(updated)


async def delete_staff_user(user_id: str):
    """Delete a staff user. Only staff accounts (manager/verification) can be deleted."""
    db = await get_db()
    filt = user_id_filter(user_id)
    
    user = await db.staff_users.find_one(filt)
    if not user:
        raise HTTPException(status_code=404, detail="Staff user not found")
    
    if user.get("role") not in [Roles.ADMIN, Roles.MANAGER, Roles.VERIFICATION]:
        raise HTTPException(status_code=400, detail="Cannot delete non-staff users")
    
    result = await db.staff_users.delete_one(filt)
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    return {"success": True, "message": f"Staff member {user.get('full_name', user_id)} deleted successfully"}
