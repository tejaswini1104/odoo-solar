import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api.api_router import api_router

# Ensure tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0-phase1",
    description="Solar Installation Management System — Phase 1 Vertical Slice"
)

# CORS middleware for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Photos and signatures are stored under the media folder but are NOT served as public static files.
# They are returned only through endpoints that check who is asking.
if not os.path.exists(settings.MEDIA_DIR):
    os.makedirs(settings.MEDIA_DIR, exist_ok=True)

# Mount API router
app.include_router(api_router)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "phase": "Phase 1 - Core Installation & Lifecycle Engine",
        "docs_url": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
