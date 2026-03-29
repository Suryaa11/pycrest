import os
from bson import ObjectId
from fastapi import HTTPException
from ..database.mongo import get_db
from ..core.config import settings


async def get_document_binary(document_id: str | ObjectId):
    db = await get_db()
    if isinstance(document_id, str):
        try:
            document_id = ObjectId(document_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.documents.find_one({"_id": document_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Support both old Binary storage and new filesystem storage
    if "file_path" in doc:
        file_path = doc["file_path"]
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                doc["data"] = f.read()
        else:
            raise HTTPException(status_code=404, detail="Document file not found on disk")
    elif "data" not in doc:
        raise HTTPException(status_code=404, detail="Document has no data")

    return doc