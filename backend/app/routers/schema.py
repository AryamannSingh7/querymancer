"""GET /databases/{database_id}/schema — structured schema for the UI.

The frontend's SchemaBrowser fetches this on mount so users can browse
tables, columns, and FK relationships while composing queries. Re-uses
executor's path resolver so the same whitelist-by-existence rule applies.
"""

from fastapi import APIRouter, HTTPException, status

from app.core import executor
from app.core.introspect import TableInfo, introspect

router = APIRouter()


@router.get(
    "/databases/{database_id}/schema",
    response_model=list[TableInfo],
)
def get_schema(database_id: str) -> list[TableInfo]:
    try:
        path = executor._resolve_db_path(database_id)
    except executor.ExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return introspect(path)
