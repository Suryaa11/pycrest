from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.security import require_roles
from app.database.mongo import get_db
from app.models.enums import Roles
from app.services.audit_service import list_audit_logs
from app.utils.serializers import normalize_doc

router = APIRouter()


def parse_dt(v: str | None):
    from datetime import datetime

    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {v}") from exc


@router.get("/audit-logs")
async def audit_logs(
    date_from: str | None = None,
    date_to: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    entity_id: str | None = None,
    limit: int = 200,
    page: int | None = None,
    next_cursor: str | None = None,
    user=Depends(require_roles(Roles.ADMIN)),
):
    parsed_from = parse_dt(date_from)
    parsed_to = parse_dt(date_to)
    db = await get_db()
    filt: dict = {}
    if parsed_from or parsed_to:
        filt["created_at"] = {}
        if parsed_from:
            filt["created_at"]["$gte"] = parsed_from
        if parsed_to:
            filt["created_at"]["$lte"] = parsed_to
    if actor_id:
        filt["actor_id"] = str(actor_id)
    if action:
        filt["action"] = action
    if entity_id:
        filt["entity_id"] = str(entity_id)

    safe_limit = max(1, min(int(limit or 200), 1000))
    if page is not None and page >= 1:
        skip = (page - 1) * safe_limit
        docs = (
            await db.audit_logs.find(filt)
            .sort([("created_at", -1), ("_id", -1)])
            .skip(skip)
            .to_list(length=safe_limit)
        )
        items = [normalize_doc(l) for l in docs]
        total = await db.audit_logs.count_documents(filt)
        return {"items": items, "total": total, "page": page, "page_size": safe_limit}

    return await list_audit_logs(
        date_from=parsed_from,
        date_to=parsed_to,
        actor_id=actor_id,
        action=action,
        entity_id=entity_id,
        limit=limit,
        next_cursor=next_cursor,
    )


@router.get("/audit-logs/export")
async def audit_logs_export(
    date_from: str | None = None,
    date_to: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    entity_id: str | None = None,
    limit: int = 2000,
    user=Depends(require_roles(Roles.ADMIN)),
):
    import csv
    import io

    parsed_from = parse_dt(date_from)
    parsed_to = parse_dt(date_to)
    res = await list_audit_logs(
        date_from=parsed_from,
        date_to=parsed_to,
        actor_id=actor_id,
        action=action,
        entity_id=entity_id,
        limit=limit,
    )
    items = res.get("items") if isinstance(res, dict) else res

    def iter_csv():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["created_at", "action", "actor_role", "actor_id", "entity_type", "entity_id", "details"])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        for it in items:
            writer.writerow(
                [
                    it.get("created_at"),
                    it.get("action"),
                    it.get("actor_role"),
                    it.get("actor_id"),
                    it.get("entity_type"),
                    it.get("entity_id"),
                    ("" if not it.get("details") else str(it.get("details")).replace("\n", " ")),
                ]
            )
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )
