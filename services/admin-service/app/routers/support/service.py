from datetime import datetime
from fastapi import HTTPException
from app.database.mongo import get_db
from app.models.enums import Roles
from app.services.audit_service import write_audit_log
from app.utils.serializers import normalize_doc

async def list_support_tickets(status="all", customer_id=None):
    db = await get_db()
    filt = {}
    if status != "all": filt["status"] = status
    if customer_id: filt["customer_id"] = str(customer_id)
    rows = await db.support_tickets.find(filt).sort("created_at", -1).to_list(length=500)
    return [normalize_doc(r) for r in rows]

async def resolve_ticket(ticket_id: str, payload, admin_user):
    db = await get_db()
    doc = await db.support_tickets.find_one({"ticket_id": ticket_id})
    if not doc: raise HTTPException(status_code=404, detail="Ticket not found")

    now = datetime.utcnow()
    update = {"admin_reply": payload.reply_message.strip(), "updated_at": now}
    if payload.close_ticket:
        update.update({"status": "closed", "resolved_at": now, "resolved_by": str(admin_user.get("_id"))})
    
    await db.support_tickets.update_one({"ticket_id": ticket_id}, {"$set": update})
    await write_audit_log(
        action="support_ticket_resolved" if payload.close_ticket else "support_ticket_replied",
        actor_role=Roles.ADMIN,
        actor_id=str(admin_user.get("_id")),
        entity_type="support_ticket",
        entity_id=ticket_id,
        details={"customer_id": str(doc.get("customer_id") or ""), "closed": payload.close_ticket}
    )
    return normalize_doc(await db.support_tickets.find_one({"ticket_id": ticket_id}))
