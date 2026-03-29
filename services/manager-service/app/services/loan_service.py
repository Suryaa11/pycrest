from ..database.mongo import get_db
from fastapi import HTTPException
from ..utils.id import loan_id_filter
from datetime import datetime


async def assign_verification(loan_collection: str, loan_id: str, verification_id: str, manager_id):
    db = await get_db()
    filt = loan_id_filter(loan_id)
    result = await db[loan_collection].update_one(
        filt,
        {"$set": {
            "assigned_verification_id": str(verification_id),
            "status": "assigned_to_verification",
            "assigned_at": datetime.utcnow(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Loan not found")
    return await db[loan_collection].find_one(filt)


async def manager_approve_or_reject(loan_collection: str, loan_id: str, manager_id, approve: bool):
    db = await get_db()
    filt = loan_id_filter(loan_id)
    status = "pending_admin_approval" if approve else "rejected"
    result = await db[loan_collection].update_one(
        filt,
        {"$set": {
            "status": status,
            "manager_id": str(manager_id),
            "manager_reviewed_at": datetime.utcnow(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Loan not found")
    return await db[loan_collection].find_one(filt)


async def manager_forward_to_admin(loan_collection: str, loan_id: str, manager_id, recommendation=None, remarks=None):
    db = await get_db()
    filt = loan_id_filter(loan_id)
    result = await db[loan_collection].update_one(
        filt,
        {"$set": {
            "status": "pending_admin_approval",
            "manager_recommendation": recommendation,
            "manager_remarks": remarks,
            "manager_id": str(manager_id),
            "forwarded_at": datetime.utcnow(),
        }}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Loan not found")
    return await db[loan_collection].find_one(filt)


async def manager_verify_signed_sanction(loan_id: str, manager_id, approve: bool, remarks=None):
    db = await get_db()
    for collection in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loan = await db[collection].find_one(loan_id_filter(loan_id))
        if loan:
            status = "ready_for_disbursement" if approve else "signature_rejected"
            await db[collection].update_one(
                {"_id": loan["_id"]},
                {"$set": {
                    "status": status,
                    "signature_verified_by": str(manager_id),
                    "signature_remarks": remarks,
                    "signature_verified_at": datetime.utcnow(),
                }}
            )
            return await db[collection].find_one({"_id": loan["_id"]})
    raise HTTPException(status_code=404, detail="Loan not found")


async def compute_customer_eligibility(customer_id: str):
    db = await get_db()
    try:
        cid = int(customer_id)
    except Exception:
        cid = customer_id
    kyc = await db.kyc_details.find_one({"customer_id": cid})
    if not kyc:
        raise HTTPException(status_code=404, detail="KYC not found for this customer")
    monthly_income = float(kyc.get("monthly_income") or 0)
    return {
        "customer_id": customer_id,
        "cibil_score": kyc.get("cibil_score", 0),
        "total_score": kyc.get("total_score", 0),
        "loan_eligible": kyc.get("loan_eligible", False),
        "kyc_status": kyc.get("kyc_status", "pending"),
        "suggested_max_loan": round(monthly_income * 24, 2),
        "score": kyc.get("total_score", 0),
    }