from fastapi import APIRouter, Depends, HTTPException
from typing import Literal

from app.core.security import require_roles
from app.database.mongo import get_db
from app.models.enums import Roles
from app.schemas.support import SupportTicketAdminResolve
from app.services.audit_service import write_audit_log
from app.utils.serializers import normalize_doc

router = APIRouter()


@router.get("/support/tickets")
async def admin_support_tickets(
    status: Literal["all", "open", "closed"] = "all",
    customer_id: str | None = None,
    user=Depends(require_roles(Roles.ADMIN)),
):
    db = await get_db()
    filt: dict = {}
    if status != "all":
        filt["status"] = status
    if customer_id:
        filt["customer_id"] = str(customer_id)
    rows = await db.support_tickets.find(filt).sort([("created_at", -1), ("_id", -1)]).to_list(length=500)
    return [normalize_doc(r) for r in rows]


@router.post("/support/tickets/{ticket_id}/resolve")
async def admin_resolve_support_ticket(
    ticket_id: str,
    payload: SupportTicketAdminResolve,
    user=Depends(require_roles(Roles.ADMIN)),
):
    from datetime import datetime

    db = await get_db()
    doc = await db.support_tickets.find_one({"ticket_id": ticket_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Ticket not found")

    now = datetime.utcnow()
    update: dict = {"admin_reply": payload.reply_message.strip(), "updated_at": now}
    if payload.close_ticket:
        update["status"] = "closed"
        update["resolved_at"] = now
        update["resolved_by"] = str(user.get("_id"))
    else:
        update["status"] = "open"

    await db.support_tickets.update_one({"ticket_id": ticket_id}, {"$set": update})
    updated = await db.support_tickets.find_one({"ticket_id": ticket_id})
    await write_audit_log(
        action="support_ticket_resolved" if payload.close_ticket else "support_ticket_replied",
        actor_role=Roles.ADMIN,
        actor_id=str(user.get("_id")),
        entity_type="support_ticket",
        entity_id=ticket_id,
        details={"customer_id": str(doc.get("customer_id") or ""), "closed": bool(payload.close_ticket)},
    )
    return normalize_doc(updated or {})
