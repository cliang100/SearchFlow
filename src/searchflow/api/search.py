from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel

from ..search.search import SearchEngine
from ..database.connection import SessionLocal
from ..database.models import Document

router = APIRouter(prefix="/search", tags=["search"])

class SearchResponse(BaseModel):
    id: int
    title: str
    url: str
    content: str
    score: float
    
class AutocompleteResponse(BaseModel):
    suggestions: List[str]
    
search_engine = None

def get_search_engine():
    global search_engine
    if search_engine is None:
        search_engine = SearchEngine()
    return search_engine

@router.get("/", response_model=List[SearchResponse])
async def search_documents(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results")
):
    """Search documents"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    engine = get_search_engine()
    results = engine.search(q, limit)
    
    return results

@router.get("/autocomplete", response_model=AutocompleteResponse)
async def autocomplete_suggestions(
    q: str = Query(..., description="Prefix for autocomplete"),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions")
):
    """Get autocomplete suggestions"""
    if not q.strip():
        raise HTTPException(status_code=400, detail="Prefix cannot be empty")

    engine = get_search_engine()
    suggestions = engine.autocomplete(q)
    
    return AutocompleteResponse(suggestions=suggestions[:limit])

@router.post("/rebuild-index")
async def rebuild_index():
    """Rebuild the search index from the current database contents"""
    global search_engine
    search_engine = SearchEngine()
    return {"message": f"Index rebuilt with {search_engine.index.doc_count} documents"}