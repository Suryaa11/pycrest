from app.database.mongo import get_db
from app.utils.serializers import normalize_doc

async def list_audit_logs(
    date_from=None,
    date_to=None,
    actor_id=None,
    action=None,
    entity_id=None,
    limit=200,
    next_cursor=None,
):
    db = await get_db()
    filt: dict = {}
    if date_from or date_to:
        filt["created_at"] = {}
        if date_from: filt["created_at"]["$gte"] = date_from
        if date_to: filt["created_at"]["$lte"] = date_to
    if actor_id: filt["actor_id"] = str(actor_id)
    if action: filt["action"] = action
    if entity_id: filt["entity_id"] = str(entity_id)

    safe_limit = max(1, min(int(limit or 200), 2000))
    cursor = db.audit_logs.find(filt).sort([("created_at", -1), ("_id", -1)])
    
    docs = await cursor.to_list(length=safe_limit)
    items = [normalize_doc(d) for d in docs]
    total = await db.audit_logs.count_documents(filt)
    
    return {"items": items, "total": total}
