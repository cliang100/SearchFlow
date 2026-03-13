from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database.connection import get_db
from ..database.models import Document
from ..schemas import DocumentCreate, DocumentUpdate, DocumentResponse, SearchQuery, SearchResponse
import hashlib

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/", response_model=DocumentResponse, status_code=201)
def create_document(document: DocumentCreate, db: Session = Depends(get_db)):
    # Generate content hash
    content_hash = hashlib.sha256(document.content.encode()).hexdigest() if document.content else None
    
    # Check for duplicate URL or content
    existing = db.query(Document).filter(
        (Document.url == str(document.url)) |
        (Document.content_hash == content_hash)
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Document with this URL or content already exists")

    # Create new document
    db_document = Document(
        url=str(document.url),
        title=document.title,
        content=document.content,
        content_hash=content_hash,
        crawl_depth=document.crawl_depth,
        word_count=len(document.content.split()) if document.content else 0
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return db_document

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    documents = db.query(Document).offset(skip).limit(limit).all()
    return documents

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    db.delete(document)
    db.commit()
    
@router.get("/search/", response_model=SearchResponse)
def search_documents(
    q: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Simple text search for now
    documents = db.query(Document).filter(
        Document.content.ilike(f"%{q}%") |
        Document.title.ilike(f"%{q}%") 
    ).offset(skip).limit(limit).all()

    total = db.query(Document).filter(
        Document.content.ilike(f"%{q}%") |
        Document.title.ilike(f"%{q}%")
    ).count()
    
    return SearchResponse(
        documents=documents,
        total=total,
        query=q,
        limit=limit,
        offset=skip
    )

@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_update: DocumentUpdate,
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update fields
    update_data = document_update.dict(exclude_unset=True)
    
    if "content" in update_data:
        # Recalculate content hash and word count
        update_data["content_hash"] = hashlib.sha256(update_data["content"].encode()).hexdigest()
        update_data["word_count"] = len(update_data["content"].split())
    
    for field, value in update_data.items():
        setattr(document, field, value)
        
    db.commit()
    db.refresh(document)
    
    return document
