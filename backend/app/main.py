"""
TENeT Backend API - Telehealth Effectiveness & Necessity Tracker

FastAPI application for serving community healthcare and connectivity data.

Design principles:
- Research/prototype oriented
- Raw data exposure (no derived scores)
- Explicit confidence tracking
- Transparent handling of missing data
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.communities import router as communities_router
from app.data_store import data_store
from app.ingestion import load_sample_data


# Initialize FastAPI app
app = FastAPI(
    title="TENeT API",
    description="Backend API for Telehealth Effectiveness & Necessity Tracker",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routes
app.include_router(communities_router)


@app.on_event("startup")
async def startup_event():
    """
    Initialize data on startup.
    
    In production, this would connect to databases or external APIs.
    For prototype, we load sample data.
    """
    count = load_sample_data(data_store)
    print(f"✓ Loaded {count} communities into data store")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "TENeT API",
        "version": "0.1.0",
        "description": "Telehealth Effectiveness & Necessity Tracker",
        "docs": "/api/docs",
        "endpoints": {
            "communities": "/api/communities",
            "health": "/api/health"
        }
    }
