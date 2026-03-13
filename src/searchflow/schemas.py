from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class DocumentBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    content: Optional[str] = None
    crawl_depth: int = 1
    
class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    crawl_depth: Optional[int] = None

class DocumentResponse(DocumentBase):
    id: int
    content_hash: Optional[str] = None
    crawled_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    word_count: Optional[int] = None
    
    class Config:
        from_attributes = True
        
class SearchQuery(BaseModel):
    query: str
    limit: int = 10
    offset: int = 0
    
class SearchResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    query: str
    limit: int
    offset: int