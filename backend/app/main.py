"""
TENeT Backend API - Telehealth Effectiveness & Necessity Tracker

FastAPI application for serving community healthcare and connectivity data.

Design principles:
- Research/prototype oriented
- Raw data exposure (no derived scores)
- Explicit confidence tracking
- Transparent handling of missing data
- Season-aware analysis
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.routes.communities import router as communities_router
from app.database import init_db, get_db
from app.data_store import data_store
from app.ingestion import load_sample_data

# New modular routers
from api.equity_routes import router as equity_router
from api.export_routes import router as export_router
from api.search_routes import router as search_router


# Initialize FastAPI app
app = FastAPI(
    title="TENeT API",
    description="Backend API for Telehealth Effectiveness & Necessity Tracker",
    version="0.3.0",
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
app.include_router(equity_router)
app.include_router(export_router)
app.include_router(search_router)


@app.on_event("startup")
async def startup_event():
    """
    Initialize data on startup.
    
    Creates database tables and loads sample data.
    In production, data would be loaded from external APIs.
    """
    from app.digital_equity_integration import batch_update_equity_data
    from sqlalchemy.orm import Session
    
    # Initialize database
    init_db()
    print("✓ Database initialized")
    
    # Load sample data into in-memory store (backward compatibility)
    count = load_sample_data(data_store)
    print(f"✓ Loaded {count} communities into data store")
    
    # Initialize digital equity data if not already present
    try:
        from app.database import engine, SessionLocal as _SessionLocal, Community as _Community
        db = _SessionLocal()
        
        # Check if any community has equity data
        community_with_equity = db.query(_Community).filter(
            _Community.digital_equity_data.isnot(None)
        ).first()
        
        if not community_with_equity:
            print("⚙️  Computing digital equity data for all communities...")
            updated = batch_update_equity_data(db)
            print(f"✓ Digital equity data computed for {updated} communities")
        else:
            print("✓ Digital equity data already present")
        
        db.close()
    except Exception as e:
        print(f"⚠️  Could not auto-initialize digital equity data: {e}")
        print("   Run 'python migrate_digital_equity.py --populate' manually")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "TENeT API",
        "version": "0.3.0",
        "description": "Telehealth Effectiveness & Necessity Tracker",
        "features": [
            "Season-aware healthcare necessity analysis",
            "Digital Equity Layer with affordability analysis",
            "Community safety net evaluation",
            "Value index for pricing equity",
            "Sensitivity analysis / simulation engine",
            "Data transparency dashboard",
            "PDF report export",
            "Map snapshot service",
        ],
        "docs": "/api/docs",
        "endpoints": {
            "communities": "/api/communities",
            "search_autocomplete": "/api/communities/search/autocomplete?q=",
            "digital_equity": "/api/digital-equity/summary",
            "simulate": "/api/simulate?threshold=2&radius=5",
            "coverage": "/api/system/coverage",
            "snapshot": "/api/snapshot",
            "community_report": "/api/communities/{id}/report",
            "state_summary": "/api/state-summary/report",
            "health": "/api/health",
        },
        "dataset_version": "0.3.0",
    }
