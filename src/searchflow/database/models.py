from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.sql import func
from .connection import Base

class Docuemnt(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), unique=True, nullable=False, index=True)
    title = Column(String(500))
    content = Column(Text)
    content_hash = Column(String(64), unique=True, index=True)
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    indexed_at = Column(DateTime(timezone=True), server_default=func.now())
    word_count = Column(Integer)
    crawl_depth = Column(Integer, default=1)
    
class SearchLog(Base):
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)
    results_count = Column(Integer)
    search_time = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))