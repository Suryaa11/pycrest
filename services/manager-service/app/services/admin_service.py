from ..database.mongo import get_db
from ..utils.id import loan_id_filter


async def find_loan_any(loan_id: str):
    db = await get_db()
    for collection in ["personal_loans", "vehicle_loans", "education_loans", "home_loans"]:
        loan = await db[collection].find_one(loan_id_filter(loan_id))
        if loan:
            return collection, loan
    return None, None