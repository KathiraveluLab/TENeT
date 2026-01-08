# TENeT Setup Guide

## Quick Start

### Prerequisites

- Python 3.8+ 
- Node.js 16+
- npm or yarn

### One-Command Setup (macOS)

```bash
# Make startup script executable
chmod +x start-dev.sh

# Run setup and start servers
./start-dev.sh
```

This will:
1. Open backend server in one Terminal tab
2. Open frontend server in another Terminal tab
3. Display URLs for both services

---

## Manual Setup

### Step 1: Backend Setup

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

**Backend URLs:**
- API: http://localhost:8000/api
- Interactive Docs: http://localhost:8000/api/docs
- Health Check: http://localhost:8000/api/health

### Step 2: Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Create environment file (optional)
cp .env.example .env

# Start development server
npm run dev
```

**Frontend URL:**
- App: http://localhost:5173

---

## Verify Installation

### 1. Test Backend

```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Expected output:
# {"status":"healthy","communities_loaded":8}
```

### 2. Test Frontend

1. Open http://localhost:5173 in your browser
2. You should see an interactive Alaska map
3. Community markers should be visible
4. Click any marker to open the info panel

---

## Project Structure

```
TENeT/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── models.py            # Data models
│   │   ├── data_store.py        # In-memory storage
│   │   ├── ingestion.py         # Sample data
│   │   └── routes/
│   │       └── communities.py   # API endpoints
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── services/            # API client
│   │   ├── layout/              # Page layouts
│   │   └── styles/              # CSS files
│   ├── package.json
│   └── README.md
│
├── data/                        # Original GeoJSON files
├── docs/                        # Documentation
└── start-dev.sh                 # Quick start script
```

---

## Features

### Backend Features
- ✅ RESTful API with FastAPI
- ✅ 8 sample Alaska communities
- ✅ Healthcare facility data
- ✅ Internet connectivity metrics
- ✅ Transportation/access information
- ✅ Data confidence tracking
- ✅ Auto-generated API documentation
- ✅ CORS enabled for local development

### Frontend Features
- ✅ Interactive Leaflet map
- ✅ Color-coded community markers (by data completeness)
- ✅ Click to view detailed information
- ✅ Sliding info panel
- ✅ Confidence badges for data quality
- ✅ Data completeness indicators
- ✅ Handles missing data gracefully
- ✅ Raw JSON view for debugging

---

## Sample Communities

The system includes data for:

1. **Anchorage** - Major city, comprehensive data
2. **Juneau** - State capital, good coverage
3. **Bethel** - Regional hub
4. **Barrow (Utqiaġvik)** - North Slope community
5. **Nome** - Coastal hub
6. **Kotzebue** - Northwest hub
7. **Haines** - Southeast community
8. **Napakiak** - Small village, limited data

---

## API Endpoints

### GET /api/communities
List all communities (lightweight view)

```bash
curl http://localhost:8000/api/communities
```

### GET /api/communities/{id}
Get full community details

```bash
curl http://localhost:8000/api/communities/AK-02185-0001
```

### GET /api/communities/{id}/healthcare
Get healthcare data only

```bash
curl http://localhost:8000/api/communities/AK-02185-0001/healthcare
```

### GET /api/communities/{id}/connectivity
Get connectivity data only

```bash
curl http://localhost:8000/api/communities/AK-02185-0001/connectivity
```

---

## Troubleshooting

### Backend won't start

**Issue:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend won't start

**Issue:** `Cannot find module 'react'`

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Frontend can't connect to backend

**Issue:** Network errors in browser console

**Check:**
1. Backend is running on port 8000
2. Check CORS settings in `backend/app/main.py`
3. Verify `.env` file in frontend has correct API URL

### Port already in use

**Backend (port 8000):**
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

**Frontend (port 5173):**
```bash
# Find and kill process using port 5173
lsof -ti:5173 | xargs kill -9
```

---

## Development Tips

### Hot Reload
Both backend and frontend support hot reload:
- **Backend:** Automatically reloads when Python files change
- **Frontend:** Automatically refreshes when React files change

### API Documentation
Visit http://localhost:8000/api/docs for:
- Interactive API testing
- Request/response schemas
- Endpoint descriptions

### Debug Mode
- **Backend:** Check terminal for request logs
- **Frontend:** Open browser DevTools (F12) for console logs

---

## Next Steps

1. **Explore the API**
   - Visit http://localhost:8000/api/docs
   - Try different endpoints
   - Examine response schemas

2. **Test the UI**
   - Click different communities
   - Check data confidence badges
   - View raw data in expanded section

3. **Customize Data**
   - Edit `backend/app/ingestion.py`
   - Add more communities
   - Modify data fields

4. **Extend Features**
   - Add filtering/search
   - Implement data export
   - Add more data sources

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review API docs at http://localhost:8000/api/docs
3. Check browser console for frontend errors
4. Check terminal for backend errors

---

## License

See LICENSE file in project root.
