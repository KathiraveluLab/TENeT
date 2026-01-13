# TENeT Backend API

FastAPI backend for the Telehealth Effectiveness & Necessity Tracker.

## Features

- RESTful API for community healthcare and connectivity data
- Explicit confidence tracking for all data points
- Source attribution
- Auto-generated API documentation
- Sample data for 8 Alaska communities

## Quick Start

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

- `GET /api/communities` - List all communities
- `GET /api/communities/{id}` - Get community details
- `GET /api/communities/{id}/healthcare` - Healthcare data
- `GET /api/communities/{id}/connectivity` - Connectivity data
- `GET /api/health` - Health check

## Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Data Model

Communities include:
- Healthcare facilities (with confidence levels)
- Internet connectivity metrics (with sources)
- Transportation/access information
- Data completeness scores

See `app/models.py` for full schema.

## Sample Data

8 Alaska communities with diverse characteristics:
- Major cities (Anchorage, Juneau)
- Regional hubs (Bethel, Nome, Kotzebue, Utqiaġvik)
- Smaller towns (Haines, Napakiak)

Data source: `app/ingestion.py`

## Architecture

```
app/
├── main.py              # FastAPI app & startup
├── models.py            # Pydantic data models
├── data_store.py        # In-memory storage
├── ingestion.py         # Sample data loader
└── routes/
    └── communities.py   # API endpoints
```

## Development

The server runs in reload mode by default - changes to Python files will automatically restart the server.

## Testing

```bash
# Check health
curl http://localhost:8000/api/health

# Get all communities
curl http://localhost:8000/api/communities

# Get specific community
curl http://localhost:8000/api/communities/AK-02185-0001
```

## Notes

- Uses in-memory storage (data resets on restart)
- CORS enabled for local frontend development
- No authentication (prototype only)
- Sample data represents real Alaska communities
