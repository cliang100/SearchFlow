from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from .api.documents import router as documents_router
from .database.connection import engine
from .database.models import Base

load_dotenv()

app = FastAPI(
    title="SearchFlow",
    description="A web-based search engine",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)

Base.metadata.create_all(bind=engine)

@app.get("/")
async def root():
    return {"message": "SearchFlow API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 