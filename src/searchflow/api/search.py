from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import require_admin
from ..search import search

router = APIRouter(prefix="/search", tags=["search"])


class SearchResult(BaseModel):
    id: int
    title: str
    url: str
    content: str
    score: float


class AutocompleteResponse(BaseModel):
    suggestions: List[str]


# Plain def routes run in FastAPI's thread pool, so database work doesn't block the event loop.
@router.get("/", response_model=List[SearchResult])
def search_documents(
    q: str = Query(..., max_length=200, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    return search.get_engine().search(q, limit)


@router.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete_suggestions(
    q: str = Query(..., max_length=100, description="Prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions"),
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Prefix cannot be empty")
    return AutocompleteResponse(suggestions=search.get_engine().autocomplete(q.strip(), limit))


@router.post("/rebuild-index", dependencies=[Depends(require_admin)])
def rebuild_index():
    engine = search.rebuild()
    return {"message": f"Index rebuilt with {engine.index.doc_count} documents"}
