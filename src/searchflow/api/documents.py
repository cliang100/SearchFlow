import hashlib
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..database.connection import get_db
from ..database.models import Document
from ..schemas import DocumentCreate, DocumentResponse, DocumentUpdate
from ..search import search

router = APIRouter(prefix="/documents", tags=["documents"])


def content_fields(content):
    if not content:
        return {"content_hash": None, "word_count": 0}
    return {"content_hash": hashlib.sha256(content.encode()).hexdigest(), "word_count": len(content.split())}


def check_unique(db: Session, url=None, content_hash=None, exclude_id=None):
    conditions = []
    if url:
        conditions.append(Document.url == url)
    if content_hash:
        conditions.append(Document.content_hash == content_hash)
    if not conditions:
        return
    query = db.query(Document.id).filter(conditions[0] if len(conditions) == 1 else conditions[0] | conditions[1])
    if exclude_id is not None:
        query = query.filter(Document.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Document with this URL or content already exists")


@router.post("/", response_model=DocumentResponse, status_code=201, dependencies=[Depends(require_admin)])
def create_document(document: DocumentCreate, db: Session = Depends(get_db)):
    fields = content_fields(document.content)
    check_unique(db, str(document.url), fields["content_hash"])
    db_document = Document(**document.model_dump(mode="json"), **fields)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    search.rebuild()
    return db_document


@router.get("/", response_model=List[DocumentResponse])
def list_documents(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.id).offset(skip).limit(limit).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.put("/{document_id}", response_model=DocumentResponse, dependencies=[Depends(require_admin)])
def update_document(document_id: int, document_update: DocumentUpdate, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    update_data = document_update.model_dump(exclude_unset=True)
    if "content" in update_data:
        update_data.update(content_fields(update_data["content"]))
        check_unique(db, content_hash=update_data["content_hash"], exclude_id=document_id)
    for field, value in update_data.items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    search.rebuild()
    return document


@router.delete("/{document_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
    search.rebuild()
