from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status


def document_to_dict(doc: Optional[dict]) -> Optional[dict]:
    if doc is None:
        return None
    result = dict(doc)
    if "_id" in result:
        result["id"] = str(result.pop("_id"))
    return result


def parse_object_id(value: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except Exception:
        return None


def require_object_id(value: Any, field: str = "id") -> ObjectId:
    oid = parse_object_id(value)
    if oid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )
    return oid
