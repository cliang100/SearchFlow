from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class DocumentBase(BaseModel):
    url: HttpUrl
    title: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = None
    crawl_depth: int = Field(default=1, ge=1)


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = None
    crawl_depth: Optional[int] = Field(default=None, ge=1)


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_hash: Optional[str] = None
    crawled_at: Optional[datetime] = None
    indexed_at: Optional[datetime] = None
    word_count: Optional[int] = None
