from app.database.mongo import get_db
from app.models.enums import LoanStatus
from app.utils.id import loan_id_filter
from app.utils.serializers import normalize_doc

def _mask_pan(value: str | None) -> str | None:
    pan = str(value or "").strip().upper()
    if not pan:
        return None
    if len(pan) != 10:
        return pan
    return f"{pan[:2]}******{pan[-2:]}"

def _sanitize_loan_doc(doc: dict) -> dict:
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

async def find_loan_any(loan_id: str):
    db = await get_db()
    filt = loan_id_filter(loan_id)
    for col_name in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loan = await db[col_name].find_one(filt)
        if loan:
            return col_name, loan
    return None, None

async def get_admin_approvals_dashboard(days: int = 30):
    db = await get_db()
    from datetime import datetime, timedelta
    
    admin_queue_statuses = [
        LoanStatus.PENDING_ADMIN_APPROVAL,
        LoanStatus.MANAGER_APPROVED,
        LoanStatus.ADMIN_APPROVED,
        LoanStatus.SANCTION_SENT,
        LoanStatus.SIGNED_RECEIVED,
        LoanStatus.READY_FOR_DISBURSEMENT,
    ]
    
    pending = []
    for col in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        pending += await db[col].find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)

    cutoff = datetime.utcnow() - timedelta(days=int(days or 30))
    processed_statuses = [LoanStatus.ACTIVE, LoanStatus.COMPLETED, LoanStatus.FORECLOSED, LoanStatus.REJECTED]
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

    processed = []
    for col in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        processed += await db[col].find(processed_filter).sort("applied_at", -1).to_list(length=200)

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
    loans = []
    for col in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loans += await db[col].find({"status": {"$in": admin_queue_statuses}}).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]

async def list_high_value_pending():
    db = await get_db()
    filt = {"status": LoanStatus.PENDING_ADMIN_APPROVAL, "loan_amount": {"$gt": 1500000}}
    loans = []
    for col in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loans += await db[col].find(filt).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]

async def list_ready_for_disbursement():
    db = await get_db()
    filt = {"status": LoanStatus.READY_FOR_DISBURSEMENT}
    loans = []
    for col in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loans += await db[col].find(filt).to_list(length=200)
    return [_sanitize_loan_doc(l) for l in loans]
